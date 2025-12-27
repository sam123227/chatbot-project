import React, { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [load, setLoad] = useState(false);
  const [summary, setSummary] = useState([]);

  const FileChange = (e) => setFile(e.target.files[0]);

  const Upload = async () => {
    if (!file) return alert("Please select a file");

    const formData = new FormData();
    formData.append("file", file);

    setLoad(true);
    setText("");
    setSummary([]);

    try {
      const res = await fetch("http://localhost:8081/extract-file", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const textRes = await res.text();
        console.error("Backend error:", textRes);
        alert("Extraction failed");
        setLoad(false);
        return;
      }

      const data = await res.json();
      setText(data.text || "");
      setSummary(data.summary || []);
    } catch (err) {
      console.error(err);
      alert("Extraction failed");
    }

    setLoad(false);
  };

  return (
    <div style={{ padding: 20 }}>
      <h1 style={{ textAlign: "center" }}>File Text Extractor</h1>

      <input type="file" accept=".docx,.pdf" onChange={FileChange} />
      <br /><br />

      <button onClick={Upload}>Extract Text</button>

      {load && <p>Extracting text...</p>}

      {text && (
        <>
          <textarea rows="20" cols="80" value={text} readOnly />

          <h3>Summary:</h3>

          <div className="summary-box">
            <p className="summary-text">
              {summary.join(" ")}
            </p>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
