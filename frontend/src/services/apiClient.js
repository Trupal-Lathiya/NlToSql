const BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

// ── Auth helpers ─────────────────────────────────────────────────────────────

/**
 * Register a new user.
 * Returns { status: "success", user: { username, email } }
 *      or { status: "error",   message: "..." }
 */
export async function signup(username, email, password) {
  try {
    const res = await fetch(`${BASE_URL}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    return await res.json();
  } catch (err) {
    return { status: "error", message: "Cannot connect to backend. Is the server running?" };
  }
}

/**
 * Authenticate an existing user.
 * Returns { status: "success", user: { username, email } }
 *      or { status: "error",   message: "..." }
 */
export async function login(username, password) {
  try {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    return await res.json();
  } catch (err) {
    return { status: "error", message: "Cannot connect to backend. Is the server running?" };
  }
}

// ── Existing query helpers (unchanged) ───────────────────────────────────────

/**
 * Original blocking query — kept for QueryPage (non-streaming).
 */
export async function sendQuery(naturalLanguageQuery, memoryWindow = []) {
  try {
    const conversationHistory = memoryWindow.map((e) => ({
      nl_query: e.nl_query,
      sql: e.sql || null,
      summary: e.summary || null,
      retrieved_tables: e.retrieved_tables || null,
    }));

    const response = await fetch(`${BASE_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({
        natural_language_query: naturalLanguageQuery,
        conversation_history: conversationHistory,
      }),
      signal: AbortSignal.timeout(300000),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      return { status: "error", message: err.message || `Server error: ${response.status}` };
    }
    return await response.json();

  } catch (err) {
    if (err.name === "TimeoutError") {
      return { status: "error", message: "Request timed out. The query took too long." };
    }
    if (err.name === "TypeError" && err.message.includes("fetch")) {
      return { status: "error", message: "Cannot connect to backend. Is the server running?" };
    }
    return { status: "error", message: err.message };
  }
}

/**
 * Streaming query — used by ChatPage.
 */
export function sendQueryStreaming(naturalLanguageQuery, memoryWindow = [], { onResult, onSummary, onError, onDone } = {}) {
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
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify({
          natural_language_query: naturalLanguageQuery,
          conversation_history: conversationHistory,
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
          } catch {
            // malformed chunk — skip
          }
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
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({ nl_query, retrieved_tables, summary, columns }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) return { questions: [] };
    const data = await response.json();
    return data;
  } catch {
    return { questions: [] };
  }
}

export async function checkHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`, {
      headers: { "Accept": "application/json" },
    });
    return await res.json();
  } catch {
    return { status: "error" };
  }
}