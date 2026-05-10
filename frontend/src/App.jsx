import { useState } from "react";
import FileUpload from "./components/FileUpload";
import Charts from "./components/Charts";
import Chatbot from "./components/Chatbot";
import Login from "./components/Login";
import "./App.css";

function getStoredUser() {
  try {
    const raw = localStorage.getItem("fb_user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [user, setUser] = useState(getStoredUser);
  const [fileId, setFileId] = useState(null);
  const [filename, setFilename] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");

  if (!user) {
    return <Login onAuth={(u) => setUser(u)} />;
  }

  function handleLogout() {
    localStorage.removeItem("fb_token");
    localStorage.removeItem("fb_user");
    setUser(null);
  }

  async function handleUploadSuccess(id, name) {
    setFileId(id);
    setFilename(name);
    setLoading(true);
    try {
      const res = await fetch(`/analyze/${id}`);
      if (!res.ok) throw new Error(await res.text());
      setAnalysisData(await res.json());
    } catch (e) {
      console.error("Analysis failed:", e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-icon">📊</span>
          <span className="logo-text">FinanceBot</span>
        </div>
        <nav>
          {[
            { id: "dashboard", icon: "⬡", label: "Dashboard" },
            { id: "chat", icon: "💬", label: "AI Advisor" },
          ].map((tab) => (
            <button
              key={tab.id}
              className={`nav-item ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="nav-icon">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
        {fileId && (
          <div className="sidebar-file">
            <span className="file-dot" />
            <span className="file-label" title={filename}>{filename}</span>
          </div>
        )}
      </aside>

      {/* Main */}
      <main className="main">
        <header className="topbar">
          <h1 className="page-title">
            {activeTab === "dashboard" ? "Financial Dashboard" : "AI Advisor"}
          </h1>
          <div className="topbar-right">
            {fileId && <span className="badge">{filename}</span>}
            <div className="user-chip">
              <span className="user-avatar">{user.name.charAt(0).toUpperCase()}</span>
              <span className="user-name">{user.name}</span>
            </div>
            <button className="logout-btn" onClick={handleLogout} title="Sign out">
              <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                <path fillRule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 001 1h7a1 1 0 100-2H4V5h6a1 1 0 100-2H3zm11.707 4.293a1 1 0 010 1.414L13.414 10l1.293 1.293a1 1 0 01-1.414 1.414l-2-2a1 1 0 010-1.414l2-2a1 1 0 011.414 0z" clipRule="evenodd"/>
                <path fillRule="evenodd" d="M13 10a1 1 0 011-1h4a1 1 0 110 2h-4a1 1 0 01-1-1z" clipRule="evenodd"/>
              </svg>
            </button>
          </div>
        </header>

        <div className="content">
          {activeTab === "dashboard" && (
            <>
              <FileUpload onSuccess={handleUploadSuccess} />
              {loading && (
                <div className="spinner-wrap">
                  <div className="spinner" />
                  <p>Analyzing data…</p>
                </div>
              )}
              {analysisData && !loading && (
                <Charts data={analysisData} />
              )}
            </>
          )}
          {activeTab === "chat" && (
            <Chatbot fileId={fileId} />
          )}
        </div>
      </main>
    </div>
  );
}
