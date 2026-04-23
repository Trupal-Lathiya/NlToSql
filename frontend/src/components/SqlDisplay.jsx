import { useState } from "react";

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
    <div className="sql-container">
      <div className="sql-header">
        <span className="sql-label">🧾 Generated SQL</span>
        <button className="copy-btn" onClick={handleCopy}>
          {copied ? "✅ Copied!" : "📋 Copy"}
        </button>
      </div>
      <pre className="sql-code"><code>{sql}</code></pre>
      <button className="tables-toggle" onClick={() => setTablesOpen((o) => !o)}>
        {tablesOpen ? "▲" : "▼"} Tables used from Pinecone ({retrievedTables?.length || 0})
      </button>
      {tablesOpen && (
        <div className="tables-list">
          {retrievedTables?.map((t) => <span key={t} className="table-tag">{t}</span>)}
        </div>
      )}
    </div>
  );
}