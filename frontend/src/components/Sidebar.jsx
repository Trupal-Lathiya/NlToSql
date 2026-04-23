// =============================================================================
// components/Sidebar.jsx - Navigation sidebar (replaces Streamlit sidebar)
// =============================================================================

import { NavLink } from "react-router-dom";
import styles from "./Sidebar.module.css";

export default function Sidebar({ historyCount, onClearHistory }) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <span className={styles.brandIcon}>🗄️</span>
        <div>
          <div className={styles.brandName}>NL2SQL</div>
          <div className={styles.brandSub}>Natural Language → SQL</div>
        </div>
      </div>

      <nav className={styles.nav}>
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.active : ""}`
          }
        >
          <span className={styles.navIcon}>💬</span>
          Chat
        </NavLink>

        <NavLink
          to="/history"
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.active : ""}`
          }
        >
          <span className={styles.navIcon}>📜</span>
          History
          {historyCount > 0 && (
            <span className={styles.badge}>{historyCount}</span>
          )}
        </NavLink>

        <NavLink
          to="/query"
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.active : ""}`
          }
        >
          <span className={styles.navIcon}>⚡</span>
          Query Builder
        </NavLink>
      </nav>

      <div className={styles.footer}>
        {historyCount > 0 && (
          <button className={styles.clearBtn} onClick={onClearHistory}>
            🗑️ Clear Chat History
          </button>
        )}
        <div className={styles.footerNote}>
          Powered by Pinecone + Groq + SQL Server
        </div>
      </div>
    </aside>
  );
}