import { useState } from "react";

export function useHistory() {
  const [history, setHistory] = useState([]);

  const addEntry = (entry) =>
    setHistory((prev) => [...prev, { ...entry, id: Date.now() }]);

  const deleteEntry = (id) =>
    setHistory((prev) => prev.filter((e) => e.id !== id));

  const clearHistory = () => setHistory([]);

  const getMemoryWindow = () =>
    history
      .filter((e) => e.status === "success")
      .slice(-5);

  return { history, addEntry, deleteEntry, clearHistory, getMemoryWindow };
}