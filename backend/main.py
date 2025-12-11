import os
import re
import logging
import tempfile
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
import requests
import subprocess
import traceback

import spacy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# -----------------------------
# Setup directories
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "..", "assets", "images")
os.makedirs(ASSETS_DIR, exist_ok=True)
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_ASSETS_DIR = os.path.join(ASSETS_DIR, f"run_{RUN_ID}")
os.makedirs(RUN_ASSETS_DIR, exist_ok=True)

# -----------------------------
# Load API keys
# -----------------------------
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found.")
if not UNSPLASH_ACCESS_KEY:
    raise RuntimeError("UNSPLASH_ACCESS_KEY not found.")

# -----------------------------
# Setup FastAPI
# -----------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Load spaCy
# -----------------------------
nlp = spacy.load("en_core_web_sm")

# -----------------------------
# Input model
# -----------------------------
class InputText(BaseModel):
    text: str
    presentation_type: str = "general"

# -----------------------------
# Utilities
# -----------------------------
def determine_theme(keyword: str) -> str:
    keyword = keyword.lower().strip()
    education_words = ["university", "college", "school", "institute", "academy"]
    technical_words = ["machine", "learning", "ai", "data", "science", "algorithm", "compute", "cloud"]
    finance_words = ["finance", "investment", "economics", "stock", "market", "business"]
    food_words = ["food", "cook", "cooking", "recipe", "sweet potato", "vegetable", "fruit"]
    nature_words = ["forest", "mountain", "river", "city", "park", "nature", "travel"]
    soft_topics = ["psychology", "mental", "philosophy", "art", "history", "culture"]
    color_words = ["red", "blue", "green", "purple", "orange", "yellow", "brown", "black"]

    if any(w in keyword for w in education_words):
        return "structure=blue!80!black"
    if any(w in keyword for w in technical_words):
        return "structure=blue!70!black"
    if any(w in keyword for w in finance_words):
        return "structure=blue!90!black"
    if any(w in keyword for w in food_words):
        return "structure=orange!80!black"
    if any(w in keyword for w in nature_words):
        return "structure=green!50!black"
    if any(w in keyword for w in soft_topics):
        return "structure=purple!70!black"
    for c in color_words:
        if c in keyword:
            return f"structure={c}"
    return "beaver"

def extract_image_keyword(user_text: str) -> str:
    doc = nlp(user_text.lower())
    for ent in doc.ents:
        if ent.label_ == "ORG" and "university" in ent.text.lower():
            return ent.text
    for ent in doc.ents:
        if ent.label_ == "ORG":
            return ent.text
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            return ent.text
    noun_chunks = [
        chunk.text.lower().strip()
        for chunk in doc.noun_chunks
        if len(chunk.text.split()) <= 4
    ]
    blacklist = {"presentation", "introduction", "overview", "analysis", "lesson", "guide", "basics", "topic"}
    for nc in noun_chunks:
        cleaned = " ".join([w for w in nc.split() if w not in blacklist])
        if cleaned.strip():
            return cleaned.strip()
    words = [w for w in user_text.split() if w.isalpha()]
    return " ".join(words[:3]) if words else "presentation"

def download_title_image(keyword: str) -> str | None:
    local_filename = re.sub(r"[^a-zA-Z0-9_-]", "_", keyword) + ".jpg"
    local_path = os.path.join(RUN_ASSETS_DIR, local_filename)
    url = "https://api.unsplash.com/photos/random"
    params = {
        "query": keyword,
        "orientation": "landscape",
        "client_id": UNSPLASH_ACCESS_KEY
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        image_url = data["urls"]["regular"]
        img_resp = requests.get(image_url, timeout=10)
        img_resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(img_resp.content)
        logger.info(f"Downloaded title image: {local_path}")
        return local_path
    except Exception as e:
        logger.warning(f"Unsplash attempt failed for '{keyword}': {e}")
        return None

def clean_latex(latex: str) -> str:
    latex = latex.lstrip("\ufeff")
    latex = re.sub(r"^\s+", "", latex)
    match = re.search(r"\\documentclass", latex)
    if match and match.start() != 0:
        latex = latex[match.start():]
    return latex

def fix_itemize_indentation(latex: str) -> str:
    def repl(match):
        return "\\item " + match.group(1).strip()
    latex = re.sub(r"^[ \t]*\\item\s*(.*)", repl, latex, flags=re.MULTILINE)
    return latex

def normalize_itemize(latex: str) -> str:
    lines = latex.splitlines()
    normalized = []
    in_frame = False
    in_itemize = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith(r'\begin{frame}'):
            in_frame = True
            normalized.append(line)
            continue
        if stripped.startswith(r'\end{frame}'):
            if in_itemize:
                normalized.append(r'\end{itemize}')
                in_itemize = False
            in_frame = False
            normalized.append(line)
            continue
        if stripped.startswith(r'\item'):
            if not in_itemize:
                normalized.append(r'\begin{itemize}')
                in_itemize = True
            normalized.append(line)
            continue
        if stripped.startswith('\\'):
            normalized.append(line)
            continue
        if in_frame and stripped:
            if not in_itemize:
                normalized.append(r'\begin{itemize}')
                in_itemize = True
            normalized.append(r'\item ' + stripped)
            continue

        normalized.append(line)

    if in_itemize:
        normalized.append(r'\end{itemize}')

    return "\n".join(normalized)

def latex_to_pdf(latex_content: str, output_stream: BytesIO):
    latex_content = clean_latex(latex_content)
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "presentation.tex")
        pdf_path = os.path.join(tmpdir, "presentation.pdf")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_content)
        pdflatex_path = r"C:\Users\HP\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
        if not os.path.exists(pdflatex_path):
            raise RuntimeError("pdflatex not found.")
        for f_name in os.listdir(RUN_ASSETS_DIR):
            src = os.path.join(RUN_ASSETS_DIR, f_name)
            dst = os.path.join(tmpdir, f_name)
            if os.path.isfile(src):
                with open(src, "rb") as fr, open(dst, "wb") as fw:
                    fw.write(fr.read())
        for _ in range(2):
            subprocess.run(
                [pdflatex_path, "-interaction=batchmode", "-output-directory", tmpdir, tex_path],
                capture_output=True,
                text=True,
            )
        if not os.path.exists(pdf_path):
            raise RuntimeError("PDF not generated by LaTeX.")
        with open(pdf_path, "rb") as f:
            output_stream.write(f.read())

# -----------------------------
# API endpoint
# -----------------------------
@app.post("/generate-presentation-file")
async def generate_presentation_file(input: InputText):
    try:
        keyword = extract_image_keyword(input.text)
        title_image_path = download_title_image(keyword)
        theme = determine_theme(input.text)
        image_command = (
            f"\\usebackgroundtemplate{{\\includegraphics[width=\\paperwidth,height=\\paperheight]{{{os.path.basename(title_image_path)}}}}}"
            if title_image_path
            else ""
        )

        if input.presentation_type.lower() == "academic":
            style_instructions = (
        "Use a formal academic style suitable for university lectures. "
        "Include definitions, citations when possible, structured explanations, and precise terminology. "
        "Avoid conversational tone."
        )
        elif input.presentation_type.lower() == "professional":
            style_instructions = (
        "Use a polished, business-oriented style suitable for corporate presentations. "
        "Focus on clarity, actionability, insights, and concise messaging. "
        "Emphasize business value, key takeaways, and stakeholder relevance. "
        "End the presentation with a dedicated 'Next Steps' or 'Action Items' slide outlining clear, practical recommendations."
        )
        else:
            style_instructions = (
        "Use a clear, simple style that is understandable to high school students. "
        "Explain ideas using everyday language, relatable examples, and straightforward analogies. "
        "Avoid jargon, complex theory, and long technical sentences."
        )


        prompt = f"""
You are a LaTeX Beamer generation engine.
Produce ONLY valid Beamer LaTeX slides.

STRICT RULES:
- THE FIRST LINE OF YOUR OUTPUT MUST BE: \\documentclass{{beamer}}
- No characters or blank lines before it.
- Use Madrid theme for layout.
- Use the following color theme dynamically: {theme}
- Only the title slide may contain an image.
- Use this image command exactly on the title slide:
{image_command}
- Remove the authors line (\author{{}} should be empty) and remove the date line (\date{{}} should be empty).
- ASCII only. No unicode or curly quotes.
- Allowed environments: frame, itemize.
- Every \\item must be inside an itemize environment.
- Ensure proper indentation for nested itemize environments.

{style_instructions}

Convert the following content into a LaTeX Beamer presentation:
{input.text}
"""

        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "anthropic/claude-3.7-sonnet",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.3,
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw_latex = resp.json()["choices"][0]["message"]["content"]

        raw_latex = fix_itemize_indentation(raw_latex)
        raw_latex = normalize_itemize(raw_latex)

        slides_pdf = BytesIO()
        latex_to_pdf(raw_latex, slides_pdf)
        slides_pdf.seek(0)

        return StreamingResponse(
            slides_pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=presentation.pdf"},
        )

    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")