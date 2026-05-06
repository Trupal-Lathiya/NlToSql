// frontend/src/services/apiClient.js

const BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

// ── Auth helpers ──────────────────────────────────────────────────────────────

export async function signup(username, email, password) {
  try {
    const res = await fetch(`${BASE_URL}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    return await res.json();
  } catch {
    return { status: "error", message: "Cannot connect to backend. Is the server running?" };
  }
}

export async function login(username, password) {
  try {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    return await res.json();
  } catch {
    return { status: "error", message: "Cannot connect to backend. Is the server running?" };
  }
}

// ── Chat / Conversation helpers ───────────────────────────────────────────────

export async function createConversation(userId) {
  try {
    const res = await fetch(`${BASE_URL}/chats`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
    return await res.json();
  } catch {
    return { status: "error", message: "Cannot connect to backend." };
  }
}

export async function listConversations(userId) {
  try {
    const res = await fetch(`${BASE_URL}/chats/user/${userId}`);
    return await res.json();
  } catch {
    return { status: "error", conversations: [] };
  }
}

export async function getMessages(conversationId) {
  try {
    const res = await fetch(`${BASE_URL}/chats/${conversationId}/messages`);
    return await res.json();
  } catch {
    return { status: "error", messages: [] };
  }
}

export async function saveMessage({
  conversationId,
  nlQuery,
  generatedSql,
  summary,
  retrievedTables,
  columns,
  rows,
  totalRowCount,
}) {
  try {
    const res = await fetch(`${BASE_URL}/chats/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: conversationId,
        nl_query: nlQuery,
        generated_sql: generatedSql,
        summary: summary,
        retrieved_tables: retrievedTables,
        columns: columns,
        rows: rows,
        total_row_count: totalRowCount,
      }),
    });
    return await res.json();
  } catch {
    return { status: "error", message: "Cannot connect to backend." };
  }
}

export async function deleteConversation(conversationId) {
  try {
    const res = await fetch(`${BASE_URL}/chats/${conversationId}`, {
      method: "DELETE",
    });
    return await res.json();
  } catch {
    return { status: "error" };
  }
}

// ── Query helpers ─────────────────────────────────────────────────────────────
//
// Both sendQuery and sendQueryStreaming now accept an optional `user` object
// (from sessionStorage). When present, user_id and customer_id are included
// in the request body so the backend can scope every SQL query to the correct
// tenant.

/**
 * Build the tenant fields to inject into a query request body.
 * Returns { user_id, customer_id } when the user is logged in, or {} otherwise.
 */
function _tenantFields(user) {
  if (!user) return {};
  return {
    user_id: user.id || null,
    customer_id: user.customerId != null ? user.customerId : null,
  };
}

export async function sendQuery(naturalLanguageQuery, memoryWindow = [], user = null) {
  try {
    const conversationHistory = memoryWindow.map((e) => ({
      nl_query: e.nl_query,
      sql: e.sql || null,
      summary: e.summary || null,
      retrieved_tables: e.retrieved_tables || null,
    }));

    const response = await fetch(`${BASE_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({
        natural_language_query: naturalLanguageQuery,
        conversation_history: conversationHistory,
        ..._tenantFields(user),
      }),
      signal: AbortSignal.timeout(300000),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      return { status: "error", message: err.message || `Server error: ${response.status}` };
    }
    return await response.json();
  } catch (err) {
    if (err.name === "TimeoutError") return { status: "error", message: "Request timed out." };
    if (err.name === "TypeError" && err.message.includes("fetch"))
      return { status: "error", message: "Cannot connect to backend. Is the server running?" };
    return { status: "error", message: err.message };
  }
}

export function sendQueryStreaming(
  naturalLanguageQuery,
  memoryWindow = [],
  { onResult, onSummary, onError, onDone } = {},
  user = null
) {
  const controller = new AbortController();

  const conversationHistory = memoryWindow.map((e) => ({
    nl_query: e.nl_query,
    sql: e.sql || null,
    summary: e.summary || null,
    retrieved_tables: e.retrieved_tables || null,
  }));

  (async () => {
    try {
      const response = await fetch(`${BASE_URL}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({
          natural_language_query: naturalLanguageQuery,
          conversation_history: conversationHistory,
          ..._tenantFields(user),
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        onError?.({ message: err.message || `Server error: ${response.status}` });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop();
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          try {
            const json = JSON.parse(line.slice(5).trim());
            const { event, data } = json;
            if (event === "result")  onResult?.(data);
            if (event === "summary") onSummary?.(data);
            if (event === "error")   onError?.(data);
            if (event === "done")    onDone?.();
          } catch { /* malformed chunk */ }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") return;
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        onError?.({ message: "Cannot connect to backend. Is the server running?" });
        return;
      }
      onError?.({ message: err.message });
    }
  })();

  return () => controller.abort();
}

export async function getFollowupQuestions({ nl_query, retrieved_tables, summary, columns }) {
  try {
    const response = await fetch(`${BASE_URL}/query/followup-questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ nl_query, retrieved_tables, summary, columns }),
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) return { questions: [] };
    return await response.json();
  } catch {
    return { questions: [] };
  }
}

export async function checkHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`, { headers: { "Accept": "application/json" } });
    return await res.json();
  } catch {
    return { status: "error" };
  }
}