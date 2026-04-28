import { useState } from "react";
import { sendQuery } from "../services/apiClient";
import SqlDisplay from "../components/SqlDisplay";
import ResultsTable from "../components/ResultsTable";

export default function QueryPage({ addEntry }) {
  const [nlQuery, setNlQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    if (!nlQuery.trim()) return;
    setLoading(true); setResult(null);
    const res = await sendQuery(nlQuery);
    const entry = { ...res, nl_query: nlQuery, timestamp: new Date().toLocaleString() };
    setResult(entry);
    if (res.status === "success") addEntry(entry);
    setLoading(false);
  };

  return (
    <div className="query-page">
      <h1 className="query-title">⚡ Query Builder</h1>
      <p className="query-subtitle">Type a question in plain English and get SQL results instantly.</p>

      <div className="query-form">
        <label className="query-label">Your Question</label>
        <textarea
          className="query-textarea"
          placeholder="e.g. Show me all journeys with harsh braking events"
          value={nlQuery}
          onChange={(e) => setNlQuery(e.target.value)}
          rows={4}
          disabled={loading}
        />
        <button className="run-btn" onClick={handleSubmit} disabled={!nlQuery.trim() || loading}>
          {loading ? (
            <span className="loading-label"><span className="spinner" /> Embedding → Searching → Generating SQL → Executing…</span>
          ) : "Generate & Run"}
        </button>
      </div>

      {result && (
        <div className="query-results">
          <div className="result-divider" />
          {result.status === "error" ? (
            <div className="error-box">❌ {result.message}</div>
          ) : (
            <>
              <div className="success-badge">✅ Query executed successfully!</div>
              <div className="result-section">
                <div className="result-section-label">🤖 Answer</div>
                <p className="result-summary">{result.summary}</p>
              </div>
              <SqlDisplay sql={result.sql} retrievedTables={result.retrieved_tables} />
              {result.columns && result.rows != null && (
                <ResultsTable
                  columns={result.columns}
                  rows={result.rows}
                  allRows={result.all_rows}        
                  totalRowCount={result.total_row_count}
                />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}