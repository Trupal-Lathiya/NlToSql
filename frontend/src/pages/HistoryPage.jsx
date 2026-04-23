// =============================================================================
// pages/HistoryPage.jsx - Query History Page
// Replaces frontend/pages/history_page.py
// =============================================================================

import { useState } from "react";
import SqlDisplay from "../components/SqlDisplay";
import ResultsTable from "../components/ResultsTable";
import styles from "./HistoryPage.module.css";

export default function HistoryPage({ history, deleteEntry, clearHistory }) {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState(new Set());

  const toggle = (id) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const filtered = history.filter((e) => {
    if (!search.trim()) return true;
    const kw = search.toLowerCase();
    return (
      e.nl_query?.toLowerCase().includes(kw) ||
      e.sql?.toLowerCase().includes(kw) ||
      e.summary?.toLowerCase().includes(kw)
    );
  });

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>📜 Query History</h1>
          <p className={styles.subtitle}>
            {history.length} total {history.length === 1 ? "query" : "queries"} stored
          </p>
        </div>
        {history.length > 0 && (
          <button className={styles.clearAllBtn} onClick={clearHistory}>
            🗑️ Clear All
          </button>
        )}
      </div>

      {history.length === 0 ? (
        <div className={styles.empty}>
          <span>🔍</span>
          <p>No queries yet. Go to <strong>Chat</strong> to get started.</p>
        </div>
      ) : (
        <>
          <div className={styles.searchRow}>
            <input
              type="text"
              className={styles.searchInput}
              placeholder="🔎  Filter by keyword..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {filtered.length === 0 && (
            <div className={styles.noResults}>
              No results matching <strong>"{search}"</strong>
            </div>
          )}

          <div className={styles.list}>
            {filtered.map((entry, i) => {
              const isOpen = expanded.has(entry.id);
              return (
                <div key={entry.id} className={styles.card}>
                  <button
                    className={styles.cardHeader}
                    onClick={() => toggle(entry.id)}
                  >
                    <div className={styles.cardMeta}>
                      <span className={styles.cardIndex}>#{filtered.length - i}</span>
                      <span className={styles.cardQuery}>
                        {entry.nl_query?.length > 80
                          ? entry.nl_query.slice(0, 80) + "…"
                          : entry.nl_query}
                      </span>
                    </div>
                    <div className={styles.cardRight}>
                      {entry.timestamp && (
                        <span className={styles.cardTime}>🕒 {entry.timestamp}</span>
                      )}
                      {entry.status !== "error" && (
                        <span className={styles.cardRows}>
                          {entry.total_row_count ?? "?"} rows
                        </span>
                      )}
                      {entry.status === "error" && (
                        <span className={styles.cardError}>error</span>
                      )}
                      <span className={styles.chevron}>{isOpen ? "▲" : "▼"}</span>
                    </div>
                  </button>

                  {isOpen && (
                    <div className={styles.cardBody}>
                      <div className={styles.section}>
                        <span className={styles.sectionLabel}>Question</span>
                        <p className={styles.question}>{entry.nl_query}</p>
                      </div>

                      {entry.status === "error" ? (
                        <div className={styles.errorBox}>❌ {entry.message}</div>
                      ) : (
                        <>
                          {entry.summary && (
                            <div className={styles.section}>
                              <span className={styles.sectionLabel}>Answer</span>
                              <p className={styles.summaryText}>{entry.summary}</p>
                            </div>
                          )}

                          <SqlDisplay
                            sql={entry.sql}
                            retrievedTables={entry.retrieved_tables}
                          />

                          {entry.columns && entry.rows != null && (
                            <ResultsTable
                              columns={entry.columns}
                              rows={entry.rows}
                              totalRowCount={entry.total_row_count}
                            />
                          )}
                        </>
                      )}

                      <div className={styles.cardActions}>
                        <button
                          className={styles.deleteBtn}
                          onClick={() => deleteEntry(entry.id)}
                        >
                          🗑️ Delete entry
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}