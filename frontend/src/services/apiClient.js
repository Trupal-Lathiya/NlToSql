// =============================================================================
// services/apiClient.js - Backend API Communication Layer
// =============================================================================
// Replaces frontend/api_client.py
// Handles all HTTP communication with the FastAPI backend.

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

export async function sendQuery(naturalLanguageQuery) {
  try {
    const response = await fetch(`${BASE_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ natural_language_query: naturalLanguageQuery }),
      signal: AbortSignal.timeout(120000),
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

export async function checkHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    return await res.json();
  } catch {
    return { status: "error" };
  }
}