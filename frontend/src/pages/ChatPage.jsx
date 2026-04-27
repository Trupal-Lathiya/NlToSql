import { useState, useEffect, useRef } from "react";
import { sendQuery, getFollowupQuestions } from "../services/apiClient";
import SqlDisplay from "../components/SqlDisplay";
import ResultsTable from "../components/ResultsTable";

export default function ChatPage({ history, addEntry, getMemoryWindow }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [followupMap, setFollowupMap] = useState({});
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading]);

  // After a successful entry is added, fetch follow-up questions for it
  useEffect(() => {
    const lastEntry = history[history.length - 1];
    if (
      !lastEntry ||
      lastEntry.status !== "success" ||
      followupMap[lastEntry.id] !== undefined
    ) return;

    // Mark as loading so we don't re-fetch
    setFollowupMap((prev) => ({ ...prev, [lastEntry.id]: "loading" }));

    getFollowupQuestions({
      nl_query: lastEntry.nl_query,
      retrieved_tables: lastEntry.retrieved_tables || [],
      summary: lastEntry.summary || "",
      columns: lastEntry.columns || [],
    }).then((data) => {
      setFollowupMap((prev) => ({
        ...prev,
        [lastEntry.id]: data.questions || [],
      }));
    });
  }, [history]);

  const handleSend = async (queryText) => {
    const query = (queryText || input).trim();
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

  const handleFollowupClick = (question) => {
    handleSend(question);
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

        {history.map((entry, idx) => {
          const isLast = idx === history.length - 1;
          const followups = followupMap[entry.id];
          const showFollowups =
            isLast &&
            !loading &&
            entry.status === "success" &&
            Array.isArray(followups) &&
            followups.length > 0;

          return (
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

                      {/* Follow-up questions chips */}
                      {showFollowups && (
                        <div className="followup-questions">
                          <div className="followup-questions-label">💡 Suggested follow-ups</div>
                          <div className="followup-chips">
                            {followups.map((q, i) => (
                              <button
                                key={i}
                                className="followup-chip"
                                onClick={() => handleFollowupClick(q)}
                                disabled={loading}
                              >
                                {q}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Loading state for follow-up questions */}
                      {isLast && !loading && followups === "loading" && entry.status === "success" && (
                        <div className="followup-questions-loading">
                          <span className="followup-dot" /><span className="followup-dot" /><span className="followup-dot" />
                          <span style={{ fontSize: "0.75rem", color: "var(--color-text-secondary, #64748b)", marginLeft: "6px" }}>
                            Generating follow-up suggestions...
                          </span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
              <div className="msg-divider" />
            </div>
          );
        })}

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
            onClick={() => handleSend()}
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