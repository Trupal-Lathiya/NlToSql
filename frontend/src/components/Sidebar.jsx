import { NavLink } from "react-router-dom";

export default function Sidebar({ historyCount, onClearHistory, user, onLogout }) {
  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="brand">
        <span className="brand-icon">🗄️</span>
        <div>
          <div className="brand-name">NL2SQL</div>
          <div className="brand-sub">Natural Language → SQL</div>
        </div>
      </div>

      {/* Navigation */}
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

      {/* Footer */}
      <div className="sidebar-footer">
        {historyCount > 0 && (
          <button className="clear-history-btn" onClick={onClearHistory}>
            🗑️ Clear Chat History
          </button>
        )}

        {/* User info + logout */}
        {user && (
          <div className="sidebar-user">
            <div className="sidebar-user-info">
              <span className="sidebar-user-avatar">👤</span>
              <span className="sidebar-user-name">{user.username}</span>
            </div>
            <button className="sidebar-logout-btn" onClick={onLogout} title="Sign out">
              ↩ Logout
            </button>
          </div>
        )}

        <div className="sidebar-note">Powered by Pinecone + Groq + SQL Server</div>
      </div>
    </aside>
  );
}