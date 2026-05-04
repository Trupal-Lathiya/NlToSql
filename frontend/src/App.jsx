import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useHistory } from "./hooks/useHistory";
import Sidebar from "./components/Sidebar";
import ChatPage from "./pages/ChatPage";
import HistoryPage from "./pages/HistoryPage";
import QueryPage from "./pages/QueryPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";

// ── Protected Route wrapper ──────────────────────────────────────────────────
function PrivateRoute({ user, children }) {
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { history, addEntry, updateEntry, clearHistory, deleteEntry, getMemoryWindow } = useHistory();

  // Auth state — persisted in sessionStorage so a page refresh keeps you logged in
  const [user, setUser] = useState(() => {
    try {
      const stored = sessionStorage.getItem("nl2sql_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const handleLogin = (userData) => {
    setUser(userData);
    sessionStorage.setItem("nl2sql_user", JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    sessionStorage.removeItem("nl2sql_user");
    clearHistory();
  };

  return (
    <BrowserRouter>
      <Routes>
        {/* ── Public auth routes ─────────────────────────────────────────── */}
        <Route
          path="/login"
          element={
            user ? <Navigate to="/" replace /> : <LoginPage onLogin={handleLogin} />
          }
        />
        <Route
          path="/signup"
          element={
            user ? <Navigate to="/" replace /> : <SignupPage onLogin={handleLogin} />
          }
        />

        {/* ── Protected app routes ───────────────────────────────────────── */}
        <Route
          path="/*"
          element={
            <PrivateRoute user={user}>
              <div className="layout">
                <Sidebar
                  historyCount={history.length}
                  onClearHistory={clearHistory}
                  user={user}
                  onLogout={handleLogout}
                />
                <main className="main">
                  <Routes>
                    <Route
                      path="/"
                      element={
                        <ChatPage
                          history={history}
                          addEntry={addEntry}
                          updateEntry={updateEntry}
                          getMemoryWindow={getMemoryWindow}
                        />
                      }
                    />
                    <Route
                      path="/history"
                      element={
                        <HistoryPage
                          history={history}
                          deleteEntry={deleteEntry}
                          clearHistory={clearHistory}
                        />
                      }
                    />
                    <Route
                      path="/query"
                      element={
                        <QueryPage
                          addEntry={addEntry}
                          getMemoryWindow={getMemoryWindow}
                        />
                      }
                    />
                    {/* Fallback */}
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