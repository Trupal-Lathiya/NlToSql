// frontend/src/components/Sidebar.jsx  (REPLACE your existing Sidebar.jsx)
import { useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";

/**
 * Groups conversations by date label: Today, Yesterday, Last 7 Days, Older.
 */
function groupByDate(conversations) {
  const now   = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  const week      = new Date(today); week.setDate(today.getDate() - 7);

  const groups = { Today: [], Yesterday: [], "Last 7 Days": [], Older: [] };

  for (const c of conversations) {
    const d = new Date(c.updated_at || c.created_at);
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());

    if (day >= today)          groups["Today"].push(c);
    else if (day >= yesterday) groups["Yesterday"].push(c);
    else if (day >= week)      groups["Last 7 Days"].push(c);
    else                       groups["Older"].push(c);
  }

  return groups;
}

export default function Sidebar({
  user,
  onLogout,
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  loadingConvs,
}) {
  const navigate = useNavigate();

  const handleNewChat = async () => {
    const newId = await onNewChat();
    if (newId) navigate("/");
  };

  const handleSelect = (convId) => {
    onSelectConversation(convId);
    navigate("/");
  };

  const groups = groupByDate(conversations);

  return (
    <aside className="sidebar">
      {/* ── Brand ─────────────────────────────────────────────────── */}
      <div className="brand">
        <span className="brand-icon">🗄️</span>
        <div>
          <div className="brand-name">NL2SQL</div>
          <div className="brand-sub">Natural Language → SQL</div>
        </div>
      </div>

      {/* ── New Chat button ───────────────────────────────────────── */}
      <button className="new-chat-btn" onClick={handleNewChat}>
        ✏️ New Chat
      </button>

      {/* ── Navigation links ─────────────────────────────────────── */}
      <nav className="nav">
        <NavLink to="/query" className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
          <span className="nav-icon">⚡</span> Query Builder
        </NavLink>
      </nav>

      {/* ── Conversations list ────────────────────────────────────── */}
      <div className="conv-list">
        {loadingConvs && (
          <div className="conv-loading">Loading chats…</div>
        )}

        {!loadingConvs && conversations.length === 0 && (
          <div className="conv-empty">No chats yet. Click New Chat to start.</div>
        )}

        {Object.entries(groups).map(([label, convs]) => {
          if (convs.length === 0) return null;
          return (
            <div key={label} className="conv-group">
              <div className="conv-group-label">{label}</div>
              {convs.map((conv) => (
                <div
                  key={conv.id}
                  className={`conv-item${activeConversationId === conv.id ? " conv-item--active" : ""}`}
                >
                  <button
                    className="conv-item-title"
                    onClick={() => handleSelect(conv.id)}
                    title={conv.title}
                  >
                    💬 {conv.title}
                  </button>
                  <button
                    className="conv-item-delete"
                    title="Delete chat"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conv.id);
                    }}
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {/* ── Footer: user info + logout ────────────────────────────── */}
      <div className="sidebar-footer">
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