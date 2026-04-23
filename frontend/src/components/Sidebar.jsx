import { NavLink } from "react-router-dom";

export default function Sidebar({ historyCount, onClearHistory }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-icon">🗄️</span>
        <div>
          <div className="brand-name">NL2SQL</div>
          <div className="brand-sub">Natural Language → SQL</div>
        </div>
      </div>
      <nav className="nav">
        <NavLink to="/" end className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
          <span className="nav-icon">💬</span> Chat
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
          <span className="nav-icon">📜</span> History
          {historyCount > 0 && <span className="nav-badge">{historyCount}</span>}
        </NavLink>
        <NavLink to="/query" className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
          <span className="nav-icon">⚡</span> Query Builder
        </NavLink>
      </nav>
      <div className="sidebar-footer">
        {historyCount > 0 && (
          <button className="clear-history-btn" onClick={onClearHistory}>
            🗑️ Clear Chat History
          </button>
        )}
        <div className="sidebar-note">Powered by Pinecone + Groq + SQL Server</div>
      </div>
    </aside>
  );
}