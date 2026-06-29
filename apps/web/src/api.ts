const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type ApiHealth = {
  status: string;
  service: string;
};

export type CallEvaluation = {
  call_event_id: string;
  risk_score: number;
  risk_level: string;
  caller_type: string;
  action_recommended: string;
  reason_codes: string[];
  message_for_senior: string;
};

export type RiskEvent = {
  id: string;
  senior_id: string;
  call_event_id: string | null;
  event_type: string;
  risk_score: number;
  risk_level: string;
  reason_codes: string[];
  summary: string | null;
};

export type EmergencyNotification = {
  id: string;
  risk_event_id: string;
  guardian_id: string;
  status: string;
  response: string | null;
  message: string | null;
};

export type VoiceProfile = {
  id: string;
  family_member_id: string;
  display_name: string;
  status: string;
  embedding_model: string | null;
  embedding_version: string | null;
  quality_score: number | null;
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  return parseResponse<T>(response);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail ?? `Request failed with ${response.status}`);
  }
  return data as T;
}

