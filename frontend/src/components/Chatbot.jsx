import { useState, useRef, useEffect } from "react";
import "./Chatbot.css";

const SUGGESTED = [
  "Why is my profit decreasing?",
  "Which months had the highest expenses?",
  "Is revenue growing fast enough?",
  "What are my biggest financial risks?",
];

function Message({ msg }) {
  if (msg.role === "user") {
    return (
      <div className="msg user-msg">
        <div className="bubble user-bubble">{msg.text}</div>
        <div className="avatar user-avatar">U</div>
      </div>
    );
  }

  if (msg.loading) {
    return (
      <div className="msg bot-msg">
        <div className="avatar bot-avatar">🤖</div>
        <div className="bubble bot-bubble loading-bubble">
          <span /><span /><span />
        </div>
      </div>
    );
  }

  if (msg.error) {
    return (
      <div className="msg bot-msg">
        <div className="avatar bot-avatar">🤖</div>
        <div className="bubble bot-bubble error-bubble">{msg.text}</div>
      </div>
    );
  }

  const { advice, data_context } = msg.data ?? {};

  return (
    <div className="msg bot-msg">
      <div className="avatar bot-avatar">🤖</div>
      <div className="bubble bot-bubble rich-bubble">
        {/* Health badge */}
        {advice?.profit_health && (
          <span className={`health-badge ${advice.profit_health}`}>
            {advice.profit_health.toUpperCase()}
          </span>
        )}

        {/* Summary */}
        {advice?.summary && <p className="bot-summary">{advice.summary}</p>}

        {/* Root causes */}
        {advice?.root_causes?.length > 0 && (
          <div className="section">
            <p className="section-heading">Root Causes</p>
            {advice.root_causes.map((c, i) => (
              <div key={i} className={`cause-item sev-${c.severity}`}>
                <div className="cause-header">
                  <span className="cause-label">{c.cause}</span>
                  <span className={`sev-tag ${c.severity}`}>{c.severity}</span>
                </div>
                <p className="cause-evidence">{c.evidence}</p>
              </div>
            ))}
          </div>
        )}

        {/* Suggestions */}
        {advice?.suggestions?.length > 0 && (
          <div className="section">
            <p className="section-heading">Suggestions</p>
            {advice.suggestions.map((s, i) => (
              <div key={i} className={`suggestion-item pri-${s.priority}`}>
                <div className="suggestion-header">
                  <span className="suggestion-action">{s.action}</span>
                  <span className={`pri-tag ${s.priority}`}>{s.priority.replace("_", " ")}</span>
                </div>
                <p className="suggestion-impact">Expected: {s.expected_impact}</p>
              </div>
            ))}
          </div>
        )}

        {/* Outlook */}
        {advice?.outlook && (
          <div className="outlook">
            <span className="outlook-icon">🔭</span>
            <p>{advice.outlook}</p>
          </div>
        )}

        {/* Meta */}
        {data_context && (
          <p className="meta-line">
            {data_context.months_analyzed} months analysed ·
            best: {data_context.best_month} ·
            worst: {data_context.worst_month}
            {data_context.total_anomalies > 0 && ` · ${data_context.total_anomalies} anomalies`}
          </p>
        )}
      </div>
    </div>
  );
}

export default function Chatbot({ fileId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(question) {
    const q = (question ?? input).trim();
    if (!q || loading) return;
    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", text: q },
      { role: "bot", loading: true },
    ]);
    setLoading(true);

    try {
      if (!fileId) throw new Error("Please upload a CSV file first (go to Dashboard tab).");

      const url = `/ask/${fileId}?question=${encodeURIComponent(q)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Request failed");

      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "bot", data },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "bot", error: true, text: e.message },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chatbot">
      {/* Suggested prompts */}
      {messages.length === 0 && (
        <div className="chat-welcome">
          <div className="welcome-icon">💬</div>
          <h2>Ask your AI Financial Advisor</h2>
          <p>Upload a CSV on the Dashboard, then ask questions below.</p>
          <div className="suggestions">
            {SUGGESTED.map((s) => (
              <button key={s} className="suggestion-chip" onClick={() => send(s)}>
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="message-list">
        {messages.map((m, i) => (
          <Message key={i} msg={m} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="input-bar">
        <input
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask about your finances…"
          disabled={loading}
        />
        <button
          className={`send-btn ${loading ? "loading" : ""}`}
          onClick={() => send()}
          disabled={loading || !input.trim()}
        >
          {loading ? <span className="btn-spinner" /> : "Send"}
        </button>
      </div>
    </div>
  );
}
