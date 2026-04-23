// =============================================================================
// pages/ChatPage.jsx - Main NL2SQL Chat Interface
// Replaces the main frontend/app.py Streamlit chat UI
// =============================================================================

import { useState, useEffect, useRef } from "react";
import { sendQuery } from "../services/apiClient";
import SqlDisplay from "../components/SqlDisplay";
import ResultsTable from "../components/ResultsTable";
import styles from "./ChatPage.module.css";

export default function ChatPage({ history, addEntry }) {
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

    const now = new Date();
    const timestamp = now.toTimeString().slice(0, 8);

    const result = await sendQuery(query);
    addEntry({ ...result, nl_query: query, timestamp });
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.messages}>
        {history.length === 0 && !loading && (
          <div className={styles.welcome}>
            <div className={styles.welcomeIcon}>🗄️</div>
            <h2>NL2SQL Chat</h2>
            <p>
              Ask any question about your database in plain English.
              <br />
              I'll generate SQL and return the results instantly.
            </p>
            <div className={styles.exampleChips}>
              {[
                "Show me all customers",
                "How many orders this week?",
                "List top 10 assets",
                "Count journeys with harsh braking",
              ].map((ex) => (
                <button
                  key={ex}
                  className={styles.chip}
                  onClick={() => setInput(ex)}
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((entry) => (
          <div key={entry.id} className={styles.messageGroup}>
            {/* User bubble */}
            <div className={styles.userRow}>
              <div className={styles.userBubble}>
                {entry.nl_query}
                <div className={styles.bubbleTime}>{entry.timestamp}</div>
              </div>
              <span className={styles.avatar}>👤</span>
            </div>

            {/* Assistant bubble */}
            <div className={styles.assistantRow}>
              <span className={styles.avatar}>🗄️</span>
              <div className={styles.assistantBubble}>
                {entry.status === "error" ? (
                  <div className={styles.errorMsg}>❌ {entry.message}</div>
                ) : (
                  <>
                    <div className={styles.summary}>
                      {entry.summary || "Query executed successfully."}
                    </div>

                    <div className={styles.expandSection}>
                      <SqlDisplay
                        sql={entry.sql}
                        retrievedTables={entry.retrieved_tables}
                      />
                    </div>

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

            <div className={styles.divider} />
          </div>
        ))}

        {loading && (
          <div className={styles.assistantRow}>
            <span className={styles.avatar}>🗄️</span>
            <div className={`${styles.assistantBubble} ${styles.thinking}`}>
              <div className={styles.dots}>
                <span /><span /><span />
              </div>
              <span className={styles.thinkingText}>
                Embedding → Searching → Generating SQL → Executing…
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Fixed input bar */}
      <div className={styles.inputBar}>
        <div className={styles.inputWrapper}>
          <textarea
            className={styles.textarea}
            placeholder="Ask your database anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />
          <button
            className={styles.sendBtn}
            onClick={handleSend}
            disabled={!input.trim() || loading}
          >
            ➤
          </button>
        </div>
        <div className={styles.hint}>Press Enter to send · Shift+Enter for newline</div>
      </div>
    </div>
  );
}