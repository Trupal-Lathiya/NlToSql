import { useState, useEffect, useRef } from "react";
import { sendQuery } from "../services/apiClient";
import SqlDisplay from "../components/SqlDisplay";
import ResultsTable from "../components/ResultsTable";

export default function ChatPage({ history, addEntry, getMemoryWindow }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading]);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");
    setLoading(true);

    const timestamp = new Date().toTimeString().slice(0, 8);
    const memoryWindow = getMemoryWindow();
    const memoryCount = memoryWindow.length;

    const result = await sendQuery(query, memoryWindow);
    addEntry({ ...result, nl_query: query, timestamp, memoryCount });
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="chat-page">
      <div className="chat-messages">

        {history.length === 0 && !loading && (
          <div className="chat-welcome">
            <div className="chat-welcome-icon">🗄️</div>
            <h2>NL2SQL Chat</h2>
            <p>Ask any question about your database in plain English.<br />
              I'll generate SQL and return the results instantly.</p>
            <div className="example-chips">
              {[
                "Show me all customers",
                "How many orders this week?",
                "List top 10 assets",
                "Count journeys with harsh braking"
              ].map((ex) => (
                <button key={ex} className="example-chip" onClick={() => setInput(ex)}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((entry) => (
          <div key={entry.id} className="message-group">

            {/* User bubble with memory indicator */}
            <div className="user-row">
              <div className="user-bubble">
                {entry.nl_query}
                <div className="bubble-time">
                  {entry.timestamp}
                  {entry.memoryCount > 0 && (
                    <span className="memory-badge">
                      🧠 {entry.memoryCount} quer{entry.memoryCount === 1 ? "y" : "ies"} in context
                    </span>
                  )}
                  {entry.memoryCount === 0 && (
                    <span className="memory-badge memory-badge--fresh">
                      ✨ fresh query
                    </span>
                  )}
                </div>
              </div>
              <span className="msg-avatar">👤</span>
            </div>

            {/* Assistant bubble */}
            <div className="assistant-row">
              <span className="msg-avatar">🗄️</span>
              <div className="assistant-bubble">
                {entry.status === "error" ? (
                  <div className="msg-error">❌ {entry.message}</div>
                ) : (
                  <>
                    {/* Context used indicator */}
                    {entry.memoryCount > 0 && entry.is_followup && (
                      <div className="followup-badge">
                        🔗 Follow-up — used {entry.memoryCount} previous quer{entry.memoryCount === 1 ? "y" : "ies"} as context
                      </div>
                    )}
                    {entry.memoryCount > 0 && !entry.is_followup && (
                      <div className="fresh-badge">
                        🆕 Fresh query — previous context ignored
                      </div>
                    )}
                    <div className="msg-summary">
                      {entry.summary || "Query executed successfully."}
                    </div>
                    <SqlDisplay sql={entry.sql} retrievedTables={entry.retrieved_tables} />
                    {entry.columns && entry.rows != null && (
                      <ResultsTable
                        columns={entry.columns}
                        rows={entry.rows}
                        totalRowCount={entry.total_row_count}
                      />
                    )}
                  </>
                )}
              </div>
            </div>
            <div className="msg-divider" />
          </div>
        ))}

        {loading && (
          <div className="assistant-row">
            <span className="msg-avatar">🗄️</span>
            <div className="assistant-bubble thinking">
              <div className="dots"><span /><span /><span /></div>
              <span className="thinking-text">
                Embedding → Searching → Generating SQL → Executing…
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        <div className="input-wrapper">
          <textarea
            className="chat-textarea"
            placeholder="Ask your database anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!input.trim() || loading}
          >
            ➤
          </button>
        </div>
        <div className="input-hint">Press Enter to send · Shift+Enter for newline</div>
      </div>
    </div>
  );
}