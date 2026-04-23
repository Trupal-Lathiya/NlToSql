// =============================================================================
// pages/QueryPage.jsx - Query Builder Page
// Replaces frontend/pages/query_page.py
// =============================================================================

import { useState } from "react";
import { sendQuery } from "../services/apiClient";
import SqlDisplay from "../components/SqlDisplay";
import ResultsTable from "../components/ResultsTable";
import styles from "./QueryPage.module.css";

export default function QueryPage({ addEntry }) {
  const [nlQuery, setNlQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    if (!nlQuery.trim()) return;
    setLoading(true);
    setResult(null);

    const res = await sendQuery(nlQuery);
    const timestamp = new Date().toLocaleString();
    const entry = { ...res, nl_query: nlQuery, timestamp };
    setResult(entry);
    if (res.status === "success") addEntry(entry);
    setLoading(false);
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>⚡ Query Builder</h1>
      <p className={styles.subtitle}>
        Type a question in plain English and get SQL results instantly.
      </p>

      <div className={styles.form}>
        <label className={styles.label}>Your Question</label>
        <textarea
          className={styles.textarea}
          placeholder="e.g. Show me all journeys with harsh braking events"
          value={nlQuery}
          onChange={(e) => setNlQuery(e.target.value)}
          rows={4}
          disabled={loading}
        />
        <button
          className={styles.runBtn}
          onClick={handleSubmit}
          disabled={!nlQuery.trim() || loading}
        >
          {loading ? (
            <span className={styles.loadingLabel}>
              <span className={styles.spinner} /> Embedding → Searching → Generating SQL → Executing…
            </span>
          ) : (
            "Generate & Run"
          )}
        </button>
      </div>

      {result && (
        <div className={styles.results}>
          <div className={styles.divider} />

          {result.status === "error" ? (
            <div className={styles.errorBox}>❌ {result.message}</div>
          ) : (
            <>
              <div className={styles.successBadge}>✅ Query executed successfully!</div>

              <div className={styles.section}>
                <div className={styles.sectionLabel}>🤖 Answer</div>
                <p className={styles.summary}>{result.summary}</p>
              </div>

              <SqlDisplay sql={result.sql} retrievedTables={result.retrieved_tables} />

              {result.columns && result.rows != null && (
                <ResultsTable
                  columns={result.columns}
                  rows={result.rows}
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