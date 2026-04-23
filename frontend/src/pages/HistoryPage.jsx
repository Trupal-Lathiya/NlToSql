import { useState } from "react";
import SqlDisplay from "../components/SqlDisplay";
import ResultsTable from "../components/ResultsTable";

export default function HistoryPage({ history, deleteEntry, clearHistory }) {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState(new Set());

  const toggle = (id) => setExpanded((prev) => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const filtered = history.filter((e) => {
    if (!search.trim()) return true;
    const kw = search.toLowerCase();
    return e.nl_query?.toLowerCase().includes(kw) || e.sql?.toLowerCase().includes(kw) || e.summary?.toLowerCase().includes(kw);
  });

  return (
    <div className="history-page">
      <div className="history-header">
        <h1 className="history-title">📜 Query History</h1>
        {history.length > 0 && <button className="history-clear-btn" onClick={clearHistory}>🗑️ Clear All</button>}
      </div>

      {history.length === 0 ? (
        <div className="history-empty">No queries yet. Go to Chat to get started.</div>
      ) : (
        <>
          <input className="history-search" placeholder="🔎 Search history..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <div className="history-list">
            {filtered.map((entry) => (
              <div key={entry.id} className="history-card">
                <div className="history-card-header" onClick={() => toggle(entry.id)}>
                  <div className="history-card-title">{entry.nl_query}</div>
                  <div className="history-card-meta">
                    <span className="history-time">🕒 {entry.timestamp}</span>
                    <span className="history-toggle">{expanded.has(entry.id) ? "▲" : "▼"}</span>
                  </div>
                </div>
                {expanded.has(entry.id) && (
                  <div className="history-card-body">
                    <div className="history-nl-query"><strong>Question:</strong> {entry.nl_query}</div>
                    {entry.status === "error" ? (
                      <div className="error-box">❌ {entry.message}</div>
                    ) : (
                      <>
                        {entry.summary && <p className="result-summary">{entry.summary}</p>}
                        <SqlDisplay sql={entry.sql} retrievedTables={entry.retrieved_tables} />
                        {entry.columns && entry.rows != null && (
                          <ResultsTable columns={entry.columns} rows={entry.rows} totalRowCount={entry.total_row_count} />
                        )}
                      </>
                    )}
                    <div className="card-actions">
                      <button className="history-delete-btn" onClick={() => deleteEntry(entry.id)}>🗑️ Delete entry</button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}