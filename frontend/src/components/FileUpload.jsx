import { useState, useRef } from "react";
import "./FileUpload.css";

export default function FileUpload({ onSuccess }) {
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);

  async function upload(file) {
    if (!file || !file.name.endsWith(".csv")) {
      setStatus("error");
      setMessage("Please upload a .csv file.");
      return;
    }
    setStatus("uploading");
    setMessage(`Uploading ${file.name}…`);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/upload", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setStatus("done");
      setMessage(`✓ ${data.filename} — ${data.rows} rows, ${data.columns.length} columns`);
      onSuccess(data.file_id, data.filename);
    } catch (e) {
      setStatus("error");
      setMessage(e.message);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    upload(e.dataTransfer.files[0]);
  }

  return (
    <div
      className={`upload-zone ${dragging ? "drag-over" : ""} ${status}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => status !== "uploading" && inputRef.current.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        hidden
        onChange={(e) => upload(e.target.files[0])}
      />

      {status === "idle" && (
        <>
          <div className="upload-icon">📁</div>
          <p className="upload-heading">Drop your CSV file here</p>
          <p className="upload-sub">or click to browse</p>
        </>
      )}
      {status === "uploading" && (
        <>
          <div className="upload-spinner" />
          <p className="upload-heading">{message}</p>
        </>
      )}
      {status === "done" && (
        <>
          <div className="upload-icon">✅</div>
          <p className="upload-heading">{message}</p>
          <p className="upload-sub">Click to upload a different file</p>
        </>
      )}
      {status === "error" && (
        <>
          <div className="upload-icon">❌</div>
          <p className="upload-heading">Upload failed</p>
          <p className="upload-sub">{message}</p>
        </>
      )}
    </div>
  );
}
