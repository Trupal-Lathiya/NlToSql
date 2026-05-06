// frontend/src/hooks/useConversations.js
import { useState, useCallback } from "react";
import {
  listConversations,
  createConversation,
  getMessages,
  deleteConversation,
} from "../services/apiClient";

/**
 * Manages the list of conversations in the sidebar and the messages
 * of whichever conversation is currently active.
 *
 * Memory window rule:
 *   - Only SUCCESSFUL messages count (status === "success" OR no status field,
 *     since messages loaded from DB don't have a status field but are all
 *     successful by definition).
 *   - Only the last 5 of those are sent to the LLM.
 *
 * IMPORTANT — logout / user-switch safety:
 *   Call resetConversations() on logout BEFORE clearing the user from state.
 *   This wipes conversations, messages and activeConversationId so the next
 *   user that logs in starts with a completely clean slate.
 */
export function useConversations(user) {
  const [conversations, setConversations]       = useState([]);
  const [activeConversationId, setActiveConvId] = useState(null);
  const [messages, setMessages]                 = useState([]);
  const [loadingConvs, setLoadingConvs]         = useState(false);
  const [loadingMsgs, setLoadingMsgs]           = useState(false);

  // ── RESET — call this on logout to wipe all state ────────────────────────
  // Without this, the previous user's conversations stay visible in React
  // memory even after sessionStorage is cleared and a new user logs in.
  const resetConversations = useCallback(() => {
    setConversations([]);
    setActiveConvId(null);
    setMessages([]);
    setLoadingConvs(false);
    setLoadingMsgs(false);
  }, []);

  // ── Load all conversations for the logged-in user ─────────────────────────
  const loadConversations = useCallback(async () => {
    if (!user?.id) return;
    setLoadingConvs(true);
    const res = await listConversations(user.id);
    // Only apply results if they belong to the CURRENT user (guard against
    // a slow in-flight request resolving after a user has already logged out).
    if (res.status === "success") {
      setConversations(res.conversations);
    }
    setLoadingConvs(false);
  }, [user]);

  // ── Create a new conversation and switch to it ────────────────────────────
  const startNewChat = useCallback(async () => {
    if (!user?.id) return null;
    const res = await createConversation(user.id);
    if (res.status !== "success") return null;

    const newConv = res.conversation;
    setConversations((prev) => [newConv, ...prev]);
    setActiveConvId(newConv.id);
    setMessages([]);
    return newConv.id;
  }, [user]);

  // ── Switch to an existing conversation ────────────────────────────────────
  const switchToConversation = useCallback(async (conversationId) => {
    if (conversationId === activeConversationId) return;
    setActiveConvId(conversationId);
    setMessages([]);
    setLoadingMsgs(true);

    const res = await getMessages(conversationId);
    if (res.status === "success") {
      const loaded = res.messages.map((m) => ({
        ...m,
        localId: m.id,
      }));
      setMessages(loaded);
    }
    setLoadingMsgs(false);
  }, [activeConversationId]);

  // ── Add a placeholder message (shown immediately while streaming) ─────────
  const addPlaceholderMessage = useCallback((localId, nlQuery, timestamp, memoryCount) => {
    setMessages((prev) => [
      ...prev,
      {
        localId,
        nl_query: nlQuery,
        timestamp,
        memoryCount,
        status: "loading",
      },
    ]);
  }, []);

  // ── Update a placeholder or existing message by localId ──────────────────
  const updateMessage = useCallback((localId, patch) => {
    setMessages((prev) =>
      prev.map((m) => (m.localId === localId ? { ...m, ...patch } : m))
    );
  }, []);

  // ── After a successful save to DB, update the conversation title in sidebar
  const refreshConversationTitle = useCallback((conversationId, newTitle) => {
    setConversations((prev) =>
      prev.map((c) =>
        c.id === conversationId
          ? { ...c, title: newTitle, updated_at: new Date().toISOString() }
          : c
      )
    );
    // Re-sort so updated convo moves to the top
    setConversations((prev) => {
      const target = prev.find((c) => c.id === conversationId);
      if (!target) return prev;
      return [target, ...prev.filter((c) => c.id !== conversationId)];
    });
  }, []);

  // ── Delete a conversation ─────────────────────────────────────────────────
  const removeConversation = useCallback(async (conversationId) => {
    await deleteConversation(conversationId);
    setConversations((prev) => prev.filter((c) => c.id !== conversationId));
    if (activeConversationId === conversationId) {
      setActiveConvId(null);
      setMessages([]);
    }
  }, [activeConversationId]);

  // ── Build the memory window from current messages ─────────────────────────
  const getMemoryWindow = useCallback(() => {
    return messages
      .filter((m) => m.status === undefined || m.status === "success")
      .slice(-5)
      .map((m) => ({
        nl_query:         m.nl_query,
        sql:              m.sql             || m.generated_sql || null,
        summary:          m.summary         || null,
        retrieved_tables: m.retrieved_tables || null,
      }));
  }, [messages]);

  return {
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
    resetConversations,   // ← expose so App.jsx can call it on logout
  };
}