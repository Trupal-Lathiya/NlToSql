// =============================================================================
// App.jsx - Root Application Component
// Replaces frontend/app.py - provides routing + shared history state
// =============================================================================

import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useHistory } from "./hooks/useHistory";
import Sidebar from "./components/Sidebar";
import ChatPage from "./pages/ChatPage";
import HistoryPage from "./pages/HistoryPage";
import QueryPage from "./pages/QueryPage";
import styles from "./App.module.css";

export default function App() {
  const { history, addEntry, clearHistory, deleteEntry } = useHistory();

  return (
    <BrowserRouter>
      <div className={styles.layout}>
        <Sidebar historyCount={history.length} onClearHistory={clearHistory} />
        <main className={styles.main}>
          <Routes>
            <Route
              path="/"
              element={<ChatPage history={history} addEntry={addEntry} />}
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
              element={<QueryPage addEntry={addEntry} />}
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}