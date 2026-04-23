// =============================================================================
// components/ResultsTable.jsx - Query Results Table Component
// Replaces frontend/components/results_table.py
// =============================================================================

import { useState } from "react";
import styles from "./ResultsTable.module.css";

export default function ResultsTable({ columns, rows, totalRowCount }) {
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState("asc");

  if (!rows || rows.length === 0) {
    return (
      <div className={styles.empty}>
        <span>🔍</span>
        <p>Query returned no results.</p>
      </div>
    );
  }

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
  };

  const sorted = [...rows].sort((a, b) => {
    if (sortCol === null) return 0;
    const idx = columns.indexOf(sortCol);
    const av = a[idx], bv = b[idx];
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortDir === "asc" ? cmp : -cmp;
  });

  const downloadCsv = () => {
    const header = columns.join(",");
    const body = rows
      .map((r) => r.map((v) => (v == null ? "" : `"${String(v).replace(/"/g, '""')}"`)).join(","))
      .join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "results.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.meta}>
        <span>
          Showing <strong>{rows.length}</strong> of <strong>{totalRowCount}</strong> rows
        </span>
        <button className={styles.downloadBtn} onClick={downloadCsv}>
          ⬇️ Download CSV
        </button>
      </div>
      <div className={styles.tableScroll}>
        <table className={styles.table}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col} onClick={() => handleSort(col)} className={styles.th}>
                  {col}
                  {sortCol === col ? (sortDir === "asc" ? " ↑" : " ↓") : " ↕"}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? styles.rowEven : styles.rowOdd}>
                {row.map((cell, j) => (
                  <td key={j} className={styles.td}>
                    {cell == null ? <span className={styles.null}>NULL</span> : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}