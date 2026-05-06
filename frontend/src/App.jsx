// frontend/src/App.jsx
import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useConversations } from "./hooks/useConversations";
import Sidebar      from "./components/Sidebar";
import ChatPage     from "./pages/ChatPage";
import QueryPage    from "./pages/QueryPage";
import LoginPage    from "./pages/LoginPage";
import SignupPage   from "./pages/SignupPage";

function PrivateRoute({ user, children }) {
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  // ── Auth state ─────────────────────────────────────────────────────────────
  const [user, setUser] = useState(() => {
    try {
      const stored = sessionStorage.getItem("nl2sql_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  // ── Conversations state ────────────────────────────────────────────────────
  const {
    conversations,
    activeConversationId,
    messages,
    loadingConvs,
    loadingMsgs,
    loadConversations,
    startNewChat,
    switchToConversation,
    addPlaceholderMessage,
    updateMessage,
    refreshConversationTitle,
    removeConversation,
    getMemoryWindow,
    resetConversations,   // ← used on logout to wipe the previous user's data
  } = useConversations(user);

  // ── Login handler ─────────────────────────────────────────────────────────
  // Reset any leftover conversation state from the previous session FIRST,
  // then set the new user so loadConversations fires for the correct userId.
  const handleLogin = (userData) => {
    resetConversations();                                         // wipe old user's data
    setUser(userData);
    sessionStorage.setItem("nl2sql_user", JSON.stringify(userData));
  };

  // ── Logout handler ────────────────────────────────────────────────────────
  // Wipe conversation/message state immediately so nothing leaks to the
  // login screen or the next user that logs in on this browser tab.
  const handleLogout = () => {
    resetConversations();                                         // clear sidebar + messages
    setUser(null);
    sessionStorage.removeItem("nl2sql_user");
  };

  // ── Load conversations whenever the logged-in user changes ────────────────
  // This runs after login (user goes from null → userData) and is a no-op
  // after logout (user is null → loadConversations guards on user?.id).
  useEffect(() => {
    if (user) {
      loadConversations();
    }
  }, [user]);

  return (
    <BrowserRouter>
      <Routes>

        {/* ── Public routes ──────────────────────────────────────── */}
        <Route
          path="/login"
          element={user ? <Navigate to="/" replace /> : <LoginPage onLogin={handleLogin} />}
        />
        <Route
          path="/signup"
          element={user ? <Navigate to="/" replace /> : <SignupPage onLogin={handleLogin} />}
        />

        {/* ── Protected routes ───────────────────────────────────── */}
        <Route
          path="/*"
          element={
            <PrivateRoute user={user}>
              <div className="layout">
                <Sidebar
                  user={user}
                  onLogout={handleLogout}
                  conversations={conversations}
                  activeConversationId={activeConversationId}
                  onNewChat={startNewChat}
                  onSelectConversation={switchToConversation}
                  onDeleteConversation={removeConversation}
                  loadingConvs={loadingConvs}
                />
                <main className="main">
                  <Routes>
                    <Route
                      path="/"
                      element={
                        <ChatPage
                          user={user}
                          activeConversationId={activeConversationId}
                          messages={messages}
                          loadingMsgs={loadingMsgs}
                          addPlaceholderMessage={addPlaceholderMessage}
                          updateMessage={updateMessage}
                          refreshConversationTitle={refreshConversationTitle}
                          getMemoryWindow={getMemoryWindow}
                          onNewChat={startNewChat}
                        />
                      }
                    />
                    <Route path="/query" element={<QueryPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </main>
              </div>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}