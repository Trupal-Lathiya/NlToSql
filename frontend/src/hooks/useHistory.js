import { useState } from "react";

export function useHistory() {
  const [history, setHistory] = useState([]);

  // Add a brand-new entry — if it already has an `id` (placeholder from streaming),
  // respect it; otherwise stamp one on.
  const addEntry = (entry) =>
    setHistory((prev) => [
      ...prev,
      { ...entry, id: entry.id ?? `entry-${Date.now()}` },
    ]);

  // Patch an existing entry by id — merges fields, never replaces the whole entry.
  // Used by the streaming flow to update a placeholder with DB results, then later
  // patch in the summary without touching anything else.
  const updateEntry = (id, patch) =>
    setHistory((prev) =>
      prev.map((e) => (e.id === id ? { ...e, ...patch } : e))
    );

  const deleteEntry = (id) =>
    setHistory((prev) => prev.filter((e) => e.id !== id));

  const clearHistory = () => setHistory([]);

  const getMemoryWindow = () =>
    history
      .filter((e) => e.status === "success")
      .slice(-5);

  return { history, addEntry, updateEntry, deleteEntry, clearHistory, getMemoryWindow };
}