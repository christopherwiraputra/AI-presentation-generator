# AI Presentation Generator

A full-stack application that converts plain-text prompts into downloadable PDF slide decks using a RAG-enhanced LaTeX Beamer pipeline.

---

## Overview

The user types a topic and selects a presentation style. The backend retrieves relevant context, generates a structured LaTeX Beamer document via an LLM, compiles it to PDF, and streams the file back to the browser for download.

```
User Prompt → React Frontend → FastAPI Backend → RAG Retrieval → LLM (OpenRouter)
    → LaTeX Beamer Source → pdflatex → PDF → Browser Download
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (Create React App) |
| Backend | FastAPI (Python) |
| LLM | Anthropic Claude 3.7 Sonnet via OpenRouter |
| RAG | Custom `rag/retriever.py` module |
| NLP | spaCy (`en_core_web_sm`) |
| Slide Format | LaTeX Beamer (Madrid theme) |
| Images | Unsplash API (title slide background) |
| PDF Compilation | MiKTeX / pdflatex |

---

## Project Structure

```
project/
├── backend/
│   ├── main.py              # FastAPI app — core generation logic
│   ├── rag/
│   │   └── retriever.py     # RAG context retrieval
│   └── .env                 # API keys (not committed)
├── frontend/
│   └── src/
│       └── App.js           # React UI
└── assets/
    └── images/              # Per-request downloaded title images
```

---

## Prerequisites

- Python 3.9+
- Node.js 16+
- [MiKTeX](https://miktex.org/) (or any TeX distribution with `pdflatex`)
- An [OpenRouter](https://openrouter.ai/) account
- An [Unsplash Developer](https://unsplash.com/developers) account

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd project
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Create a `.env` file in `backend/`:

```env
OPENROUTER_API_KEY=your_openrouter_key_here
UNSPLASH_ACCESS_KEY=your_unsplash_key_here

# Optional: override pdflatex path (defaults to MiKTeX on Windows)
PDFLATEX_PATH=C:\Users\YourName\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe

# Optional: override model (defaults to anthropic/claude-3.7-sonnet)
OPENROUTER_MODEL=anthropic/claude-3.7-sonnet
```

Start the backend:

```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

The app will be available at `http://localhost:3000`.

---

## Usage

1. Open `http://localhost:3000` in your browser.
2. Select a **Presentation Type**:
   - **Academic** — formal, structured, university-style
   - **Professional** — business-focused with action items
   - **General** — plain language for broad audiences
3. Enter a topic or description in the text area (e.g., *"Overview of neural networks for beginners"*).
4. Click **Download PDF**.
5. A progress bar tracks generation. The PDF downloads automatically when ready.

---

## How It Works

### Backend (`main.py`)

1. **Keyword extraction** — spaCy NER and noun chunking pull the most relevant keyword from the input for Unsplash image search.
2. **Theme selection** — `determine_theme()` maps topic keywords to a Beamer color theme (e.g., tech topics → blue, food → orange).
3. **RAG retrieval** — `retrieve_context()` fetches grounding text (up to 9,000 characters) to reduce hallucination.
4. **LLM prompt** — A structured prompt combining the context, style instructions, and LaTeX rules is sent to Claude via OpenRouter.
5. **LaTeX cleanup** — `clean_latex()`, `fix_itemize_indentation()`, and `normalize_itemize()` sanitize the model output before compilation.
6. **PDF compilation** — `pdflatex` runs twice in a temp directory (for layout stability). The compiled PDF is streamed back.

### Frontend (`App.js`)

- Single-page React app with a textarea, dropdown, and download button.
- A simulated progress bar (decelerating fill) provides feedback during the ~30–60 second generation window.
- The response blob is converted to an object URL and auto-downloaded.



## License

MIT
