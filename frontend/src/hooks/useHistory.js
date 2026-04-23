import { useState } from "react";

export function useHistory() {
  const [history, setHistory] = useState([]);

  const addEntry = (entry) =>
    setHistory((prev) => [...prev, { ...entry, id: Date.now() }]); // ← changed

  const deleteEntry = (id) =>
    setHistory((prev) => prev.filter((e) => e.id !== id));

  const clearHistory = () => setHistory([]);

  return { history, addEntry, deleteEntry, clearHistory };
}