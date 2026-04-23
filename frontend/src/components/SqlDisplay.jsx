// =============================================================================
// components/SqlDisplay.jsx - SQL Query Display Component
// Replaces frontend/components/sql_display.py
// =============================================================================

import { useState } from "react";
import styles from "./SqlDisplay.module.css";

export default function SqlDisplay({ sql, retrievedTables }) {
  const [copied, setCopied] = useState(false);
  const [tablesOpen, setTablesOpen] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.label}>
          <span className={styles.icon}>🧾</span> Generated SQL
        </span>
        <button className={styles.copyBtn} onClick={handleCopy}>
          {copied ? "✅ Copied!" : "📋 Copy"}
        </button>
      </div>
      <pre className={styles.codeBlock}>
        <code>{sql}</code>
      </pre>

      <button
        className={styles.tablesToggle}
        onClick={() => setTablesOpen((o) => !o)}
      >
        {tablesOpen ? "▲" : "▼"} Tables used from Pinecone ({retrievedTables?.length || 0})
      </button>

      {tablesOpen && (
        <div className={styles.tablesList}>
          {retrievedTables?.map((t) => (
            <span key={t} className={styles.tableTag}>
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}