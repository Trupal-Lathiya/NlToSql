const BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

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