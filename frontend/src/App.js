import React, { useState } from "react";
import "./App.css";
function App() {
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [summary, setSummary] = useState("");
  const [entities, setEntities] = useState({});
  const [structuredNotes, setStructuredNotes] = useState(null);

  const [showText, setShowText] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [showNER, setShowNER] = useState(false);
  const [showNotes, setShowNotes] = useState(false);

  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleUpload = async () => {
    if (!file) return alert("Please select a file");

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setText("");
    setSummary("");
    setEntities({});
    setStructuredNotes(null);
    setShowText(false);
    setShowSummary(false);
    setShowNER(false);
    setShowNotes(false);

    try {
      const res = await fetch("http://localhost:8000/extract-file", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setText(data.raw_text || "");
      setSummary(data.summary || "");
      setEntities(data.entities || {});
      setStructuredNotes(data.structured_notes || null);
    } catch {
      alert("Backend not running or CORS issue");
    }
    setLoading(false);
  };

  const handleSaveNote = async () => {
    if (!text || text.trim() === "") return alert("No content to save");

    try {
      const res = await fetch("http://localhost:8001/notes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: "demo_user",
          title: "Uploaded Document",
          content: text.trim(),
          summary: summary ? summary.trim() : "",
          entities: entities || {},
        }),
      });

      const data = await res.json();
      console.log("Backend response:", data);

      alert(" Saved successfully!");
    } catch (err) {
      console.log(err);
      alert("Failed to save note to Firebase");
    }
  };

  return (
    <div className="container">
      <h1>Document Processing & Notes Service</h1>

      <div className="upload-box">
        <input type="file" accept=".pdf,.docx" onChange={handleFileChange} />
        <button onClick={handleUpload}>
          {loading ? "Processing..." : "Upload & Process"}
        </button>
      </div>

      {loading && <p className="loading">Processing document…</p>}

      {(text || summary || Object.keys(entities).length > 0) && (
        <div className="toggle-group">
          {text && (
            <button onClick={() => setShowText(!showText)}>
              {showText ? "Hide Extracted Text" : "Show Extracted Text"}
            </button>
          )}
          {summary && (
            <button onClick={() => setShowSummary(!showSummary)}>
              {showSummary ? "Hide Summary" : "Show Summary"}
            </button>
          )}
          {Object.keys(entities).length > 0 && (
            <button onClick={() => setShowNER(!showNER)}>
              {showNER ? "Hide NER" : "Show NER"}
            </button>
          )}
          {structuredNotes && !showNotes && (
            <button onClick={() => setShowNotes(true)}>Show Notes</button>
          )}
        </div>
      )}

      {showText && (
        <div className="section">
          <h3>Extracted Text</h3>
          <textarea value={text} readOnly />
        </div>
      )}
      {showSummary && (
        <div className="section">
          <h3>Summary</h3>
          <p>{summary}</p>
        </div>
      )}
      {showNER && (
        <div className="section">
          <h3>Named Entity Recognition</h3>
          {Object.entries(entities).map(([label, vals]) => (
            <p key={label}>
              <strong>{label}:</strong> {vals.join(", ")}
            </p>
          ))}
        </div>
      )}

      {structuredNotes && showNotes && (
        <div className="section notes">
          <h2>{structuredNotes.title}</h2>
          <h3>Introduction</h3>
          <p>{structuredNotes.introduction}</p>
          {structuredNotes.sections.map((sec, idx) => (
            <div key={idx} className="note-section">
              <h3>{sec.heading}</h3>
              <ul>
                {sec.points.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          ))}
          <h3>Conclusion</h3>
          <p>{structuredNotes.conclusion}</p>

          <button
            onClick={handleSaveNote}
            style={{
              marginTop: "20px",
              backgroundColor: "#2563eb",
              color: "white",
              padding: "10px 20px",
              borderRadius: "8px",
            }}
          >
            Save
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
