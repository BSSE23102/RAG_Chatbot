// NetSol RAG Chatbot — frontend API client.
// Point this at your running FastAPI backend (see README).
// In local dev with the Vite proxy you can leave it empty ("") and calls hit /api/chat & /health.

const stored =
  typeof window !== "undefined" ? window.localStorage.getItem("netsol_backend_url") : null;

export const DEFAULT_BACKEND_URL = "";

export function getBackendUrl(): string {
  return (stored ?? DEFAULT_BACKEND_URL).replace(/\/$/, "");
}

export function setBackendUrl(url: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("netsol_backend_url", url.replace(/\/$/, ""));
  }
}

export type ChatRole = "user" | "assistant" | "system";

export interface SourceChunk {
  content: string;
  source: string | null;
  score: number | null;
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  sources: SourceChunk[];
  history: ChatMessage[];
}

/** GET /health — returns true when the backend reports { status: "ok" }. */
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${getBackendUrl()}/health`);
    if (!res.ok) return false;
    const data = (await res.json()) as { status?: string };
    return data.status === "ok";
  } catch {
    return false;
  }
}

/** POST /api/chat — sends a query and returns the RAG response. */
export async function sendChatMessage(
  sessionId: string,
  message: string,
): Promise<ChatResponse> {
  const res = await fetch(`${getBackendUrl()}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!res.ok) {
    let detail = `HTTP error ${res.status}`;
    try {
      const err = await res.json();
      if (typeof err?.detail === "string") detail = err.detail;
      else if (Array.isArray(err?.detail) && err.detail[0]?.msg) detail = err.detail[0].msg;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }

  return (await res.json()) as ChatResponse;
}
