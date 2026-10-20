export type Action = "AUTO_ANSWER" | "ESCALATE";

export interface ChatResponse {
  action: Action;
  reply: string;
  intent: string;
  confidence: number;
  sources: string[];
  reason: string | null;
  trace_id: number;
  ticket_id: number | null;
}

export interface Retrieved {
  id: string;
  score: number;
}

export interface Trace {
  id: number;
  ts: number;
  user_id: string;
  message: string;
  intent: string;
  action: Action;
  confidence: number;
  reason: string | null;
  retrieved: Retrieved[];
  cited: string[];
  latency_ms: number;
  model: string;
}

export interface Ticket {
  id: number;
  ts: number;
  user_id: string;
  message: string;
  reason: string;
  intent: string;
  status: string;
}

export interface Chunk {
  id: string;
  source: string;
  heading: string;
  text: string;
  score: number;
}

export interface Stats {
  total: number;
  auto_answered: number;
  escalated: number;
  auto_rate: number;
  avg_latency_ms: number;
  top_escalation_reasons: { reason: string; count: number }[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  chat: (message: string, userId = "web-user") =>
    request<ChatResponse>("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, user_id: userId }),
    }),
  trace: (id: number) => request<Trace>(`/traces/${id}`),
  traces: (limit = 50) => request<Trace[]>(`/traces?limit=${limit}`),
  tickets: (limit = 50) => request<Ticket[]>(`/tickets?limit=${limit}`),
  stats: () => request<Stats>("/stats"),
  chunk: (id: string) => request<Chunk>(`/chunks/${encodeURIComponent(id)}`),
};
