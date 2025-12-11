import React, { useState } from "react";

function App() {
  const [inputText, setInputText] = useState("");
  const [presentationType, setPresentationType] = useState("general");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  // ✅ smoother, more believable progress animation
  const simulateProgress = () => {
    let value = 0;
    const interval = setInterval(() => {
      // slows over time = natural feel
      const increment = Math.max(1, Math.floor((100 - value) * 0.07));
      value += increment;

      if (value >= 98) {
        value = 98; // never reach 100 until backend finishes
        clearInterval(interval);
      }
      setProgress(value);
    }, 350);
  };

  const downloadPDF = async () => {
    setError(null);
    setLoading(true);
    setProgress(0);
    simulateProgress();

    try {
      const response = await fetch(
        "http://localhost:8000/generate-presentation-file",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: inputText,
            presentation_type: presentationType,
          }),
        }
      );

      if (!response.ok) throw new Error("Backend error: " + response.status);

      const blob = await response.blob();

      // ✅ final completion moment
      setProgress(100);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "presentation.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        fontFamily: "Inter, sans-serif",
        maxWidth: 900,
        margin: "50px auto",
        padding: 40,
        background: "#FAF3DD",
        borderRadius: 22,
        backgroundImage:
          "url('https://www.transparenttextures.com/patterns/paper-fibers.png')",
      }}
    >
      <h1
        style={{
          textAlign: "center",
          fontSize: 50,
          marginBottom: 12,
          fontFamily: "'Archivo Black', sans-serif",
          letterSpacing: "0.5px",
        }}
      >
        AI Presentation Generator
      </h1>

      <p style={{ textAlign: "center", marginBottom: 38 }}>
        <span style={{ fontSize: 19 }}>
          Generate structured, downloadable PDFs from a single prompt.
        </span>
        <br />
        <span
          style={{
            fontSize: 16,
            fontStyle: "italic",
            color: "#555",
            display: "inline-block",
            marginTop: 10,
          }}
        >
          Choose the context that best fits your topic.
        </span>
      </p>

      {/* Input Area */}
      <div
        style={{
          background: "#FFFAF2",
          padding: 32,
          borderRadius: 16,
          border: "2px solid #D6CDBA",
          boxShadow: "6px 6px 0px #C7BDA7",
          marginBottom: 30,
        }}
      >
        <label style={{ fontWeight: "bold", marginRight: 10, fontSize: 16 }}>
          Presentation Type:
        </label>

        <select
          value={presentationType}
          onChange={(e) => setPresentationType(e.target.value)}
          style={{
            fontSize: "1rem",
            padding: "6px 10px",
            borderRadius: 8,
            marginBottom: 8,
            border: "1.5px solid #C7BDA7",
          }}
        >
          <option value="academic">Academic</option>
          <option value="professional">Professional</option>
          <option value="general">General</option>
        </select>

        {/* Type descriptions */}
        {presentationType === "academic" && (
          <p style={{ fontSize: 15, marginTop: 6, color: "#444" }}>
            📚 Best for school, research, education, universities, theories, or scholarly topics.
          </p>
        )}
        {presentationType === "professional" && (
          <p style={{ fontSize: 15, marginTop: 6, color: "#444" }}>
            💼 Ideal for workplace topics, business ideas, teams, strategy, or presentations at work.
          </p>
        )}
        {presentationType === "general" && (
          <p style={{ fontSize: 15, marginTop: 6, color: "#444" }}>
            🌍 Great for everyday subjects, personal interests, culture, hobbies, or broad audiences.
          </p>
        )}

        <textarea
          placeholder="Enter your presentation topic — e.g., 'USC overview, remote work trends, renewable energy policy'"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          rows={5}
          style={{
            width: "100%",
            marginTop: 16,
            padding: 16,
            fontSize: 16,
            borderRadius: 10,
            border: "1.5px solid #C7BDA7",
            boxSizing: "border-box",
          }}
        />

        <button
          onClick={downloadPDF}
          disabled={!inputText.trim() || loading}
          style={{
            marginTop: 22,
            padding: "14px 20px",
            fontSize: 18,
            borderRadius: 10,
            cursor: "pointer",
            background: loading ? "#977" : "#9B3D46",
            color: "#fff",
            border: "none",
            width: "100%",
            fontWeight: 600,
          }}
        >
          {loading ? "Creating PDF..." : "Download PDF"}
        </button>

        {loading && (
          <div style={{ marginTop: 16 }}>
            <div
              style={{
                width: "100%",
                height: 12,
                background: "#E0D8C7",
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${progress}%`,
                  height: "100%",
                  background: "#9B3D46",
                  transition: "width 0.3s ease",
                }}
              />
            </div>
            <div style={{ textAlign: "center", marginTop: 6, fontSize: 14 }}>
              {progress}%
            </div>
          </div>
        )}

        {error && (
          <div style={{ color: "#9B3D46", marginTop: 14, fontWeight: 600 }}>
            ❌ {error}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;