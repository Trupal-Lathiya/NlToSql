// frontend/src/pages/ChatPage.jsx
//
// Key multitenancy change: the `user` prop is now accepted and passed to
// sendQueryStreaming so every query carries the logged-in user's id and
// customerId to the backend.

import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { sendQueryStreaming, getFollowupQuestions, saveMessage } from "../services/apiClient";
import SqlDisplay from "../components/SqlDisplay";
import ResultsTable from "../components/ResultsTable";

export default function ChatPage({
  user,                        // ← NEW: logged-in user from App.jsx
  activeConversationId,
  messages,
  loadingMsgs,
  addPlaceholderMessage,
  updateMessage,
  refreshConversationTitle,
  getMemoryWindow,
  onNewChat,
}) {
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [followupMap, setFollowupMap] = useState({});
  const bottomRef = useRef(null);
  const navigate  = useNavigate();

  // ── Auto-scroll ───────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // ── Reset followup map when switching conversations ───────────────────────
  useEffect(() => {
    setFollowupMap({});
  }, [activeConversationId]);

  // ── Fetch follow-up suggestions for the latest message ───────────────────
  useEffect(() => {
    if (!messages.length) return;
    const lastMsg = messages[messages.length - 1];
    const localId = lastMsg.localId || lastMsg.id;

    const isSuccess = lastMsg.status === "success" || lastMsg.status === undefined;
    if (!isSuccess || !lastMsg.summary || followupMap[localId] !== undefined) return;

    setFollowupMap((prev) => ({ ...prev, [localId]: "loading" }));
    getFollowupQuestions({
      nl_query:         lastMsg.nl_query,
      retrieved_tables: lastMsg.retrieved_tables || [],
      summary:          lastMsg.summary || "",
      columns:          lastMsg.columns || [],
    }).then((data) => {
      setFollowupMap((prev) => ({ ...prev, [localId]: data.questions || [] }));
    });
  }, [messages]);

  // ── Create a new chat if none is active, then send ───────────────────────
  const ensureConversation = async () => {
    if (activeConversationId) return activeConversationId;
    const newId = await onNewChat();
    return newId;
  };

  // ── Main send handler ─────────────────────────────────────────────────────
  const handleSend = async (queryText) => {
    const query = (queryText || input).trim();
    if (!query || loading) return;
    setInput("");
    setLoading(true);

    const convId = await ensureConversation();
    if (!convId) {
      setLoading(false);
      return;
    }

    const timestamp    = new Date().toTimeString().slice(0, 8);
    const memoryWindow = getMemoryWindow();
    const memoryCount  = memoryWindow.length;
    const localId      = `local-${Date.now()}`;

    addPlaceholderMessage(localId, query, timestamp, memoryCount);

    let resultData = null;

    // Pass the logged-in user as the 4th argument so tenant IDs are sent
    sendQueryStreaming(
      query,
      memoryWindow,
      {
        onResult: (data) => {
          resultData = data;
          updateMessage(localId, {
            ...data,
            nl_query:        query,
            timestamp,
            memoryCount,
            status:          "success",
            summary:         null,
            _summaryPending: true,
          });
        },

        onSummary: async ({ summary }) => {
          updateMessage(localId, { summary, _summaryPending: false });

          if (resultData) {
            const saveRes = await saveMessage({
              conversationId:  convId,
              nlQuery:         query,
              generatedSql:    resultData.sql,
              summary:         summary,
              retrievedTables: resultData.retrieved_tables,
              columns:         resultData.columns,
              rows:            resultData.rows,
              totalRowCount:   resultData.total_row_count,
            });

            if (saveRes.status === "success") {
              refreshConversationTitle(convId, query.slice(0, 80));
            }
          }
        },

        onDone: () => setLoading(false),

        onError: (data) => {
          updateMessage(localId, {
            status:          "error",
            message:         data.message,
            _summaryPending: false,
          });
          setLoading(false);
        },
      },
      user   // ← tenant context passed here
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── Loading state while switching conversations ───────────────────────────
  if (loadingMsgs) {
    return (
      <div className="chat-page">
        <div className="chat-messages">
          <div className="chat-welcome">
            <div className="chat-welcome-icon">⏳</div>
            <p style={{ color: "#64748b" }}>Loading conversation…</p>
          </div>
        </div>
      </div>
    );
  }

  // ── No active conversation selected ──────────────────────────────────────
  if (!activeConversationId) {
    return (
      <div className="chat-page">
        <div className="chat-messages">
          <div className="chat-welcome">
            <div className="chat-welcome-icon">🗄️</div>
            <h2>NL2SQL Chat</h2>
            <p>Select a chat from the sidebar or start a new one.</p>
            <button
              className="new-chat-btn"
              style={{ marginTop: 20, alignSelf: "center" }}
              onClick={() => { onNewChat(); navigate("/"); }}
            >
              ✏️ New Chat
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-page">
      <div className="chat-messages">

        {/* ── Welcome screen when chat is empty ───────────────────── */}
        {messages.length === 0 && !loading && (
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
                "Count journeys with harsh braking",
              ].map((ex) => (
                <button key={ex} className="example-chip" onClick={() => setInput(ex)}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Messages ────────────────────────────────────────────── */}
        {messages.map((entry, idx) => {
          const localId   = entry.localId || entry.id;
          const isLast    = idx === messages.length - 1;
          const followups = followupMap[localId];
          const showFollowups =
            isLast &&
            !loading &&
            (entry.status === "success" || entry.status === undefined) &&
            !entry._summaryPending &&
            Array.isArray(followups) &&
            followups.length > 0;

          return (
            <div key={localId} className="message-group">

              {/* User bubble */}
              <div className="user-row">
                <div className="user-bubble">
                  {entry.nl_query}
                  <div className="bubble-time">
                    {entry.timestamp || ""}
                    {(entry.memoryCount > 0) && (
                      <span className="memory-badge">
                        🧠 {entry.memoryCount} quer{entry.memoryCount === 1 ? "y" : "ies"} in context
                      </span>
                    )}
                    {entry.memoryCount === 0 && (
                      <span className="memory-badge memory-badge--fresh">✨ fresh query</span>
                    )}
                  </div>
                </div>
                <span className="msg-avatar">👤</span>
              </div>

              {/* Assistant bubble */}
              <div className="assistant-row">
                <span className="msg-avatar">🗄️</span>
                <div className="assistant-bubble">
                  {entry.status === "loading" ? (
                    <div className="dots"><span /><span /><span /></div>
                  ) : entry.status === "error" ? (
                    <div className="msg-error">❌ {entry.message}</div>
                  ) : (
                    <>
                      {entry.memoryCount > 0 && entry.is_followup && (
                        <div className="followup-badge">
                          🔗 Follow-up — used {entry.memoryCount} previous quer{entry.memoryCount === 1 ? "y" : "ies"} as context
                        </div>
                      )}
                      {entry.memoryCount > 0 && !entry.is_followup && (
                        <div className="fresh-badge">🆕 Fresh query — previous context ignored</div>
                      )}

                      <div className="msg-summary">
                        {entry._summaryPending ? (
                          <span className="summary-loading">
                            <span className="followup-dot" /><span className="followup-dot" /><span className="followup-dot" />
                            <span style={{ fontSize: "0.8rem", color: "#64748b", marginLeft: "8px" }}>Generating summary…</span>
                          </span>
                        ) : (
                          entry.summary || "Query executed successfully."
                        )}
                      </div>

                      <SqlDisplay sql={entry.sql} retrievedTables={entry.retrieved_tables} />
                      {entry.columns && entry.rows != null && (
                        <ResultsTable
                          columns={entry.columns}
                          rows={entry.rows}
                          allRows={entry.all_rows}
                          totalRowCount={entry.total_row_count}
                        />
                      )}

                      {showFollowups && (
                        <div className="followup-questions">
                          <div className="followup-questions-label">💡 Suggested follow-ups</div>
                          <div className="followup-chips">
                            {followups.map((q, i) => (
                              <button
                                key={i}
                                className="followup-chip"
                                onClick={() => handleSend(q)}
                                disabled={loading}
                              >
                                {q}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {isLast && !loading && followups === "loading" &&
                        (entry.status === "success" || entry.status === undefined) &&
                        !entry._summaryPending && (
                          <div className="followup-questions-loading">
                            <span className="followup-dot" /><span className="followup-dot" /><span className="followup-dot" />
                            <span style={{ fontSize: "0.75rem", color: "#64748b", marginLeft: "6px" }}>
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

        {/* Global thinking indicator */}
        {loading && messages[messages.length - 1]?.status === "loading" && (
          <div className="assistant-row" style={{ marginTop: "-12px" }}>
            <span className="msg-avatar">🗄️</span>
            <div className="assistant-bubble thinking">
              <div className="dots"><span /><span /><span /></div>
              <span className="thinking-text">Embedding → Searching → Generating SQL → Executing…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ─────────────────────────────────────────────── */}
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