const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

let resolvedApiBaseUrl: string | null = null;
let accessToken: string | null = null;

export function setApiAccessToken(token: string | null): void {
  accessToken = token;
}

function browserBaseCandidates(): string[] {
  if (typeof window === "undefined") return [];
  return ["/soricall-api"];
}

function apiBaseCandidates(): string[] {
  return [...new Set([configuredApiBaseUrl, ...browserBaseCandidates()].filter(Boolean) as string[])];
}

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

export type UserPublic = {
  id: string;
  email: string | null;
  display_name: string;
  role: string;
  phone_number?: string | null;
};

export type Family = {
  id: string;
  name: string;
  created_by: string | null;
};

export type FamilyMember = {
  id: string;
  family_id: string;
  name: string;
  relation: string | null;
  phone_number_last4: string | null;
  is_verified: boolean;
};

export type Senior = {
  id: string;
  family_id: string;
  name: string;
  phone_number_last4: string | null;
  birth_year: number | null;
};

export type SafeWord = {
  id: string;
  family_id: string;
  hint: string | null;
};

export type FaceProfile = {
  id: string;
  family_member_id: string;
  display_name: string;
  image_ref: string | null;
  status: string;
  consent_accepted: boolean;
  match_score: number | null;
};

export type VideoVerification = {
  id: string;
  senior_id: string;
  family_member_id: string;
  risk_event_id: string | null;
  status: string;
  match_score: number | null;
  result: string;
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await requestWithFallback(path);
  return parseResponse<T>(response);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await requestWithFallback(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

export async function apiDelete(path: string): Promise<void> {
  const response = await requestWithFallback(path, { method: "DELETE" });
  await parseResponse<void>(response);
}

export function getResolvedApiBaseUrl(): string {
  return resolvedApiBaseUrl ?? apiBaseCandidates()[0] ?? "";
}

async function requestWithFallback(path: string, init?: RequestInit): Promise<Response> {
  let lastError: unknown = null;
  const candidates = resolvedApiBaseUrl ? [resolvedApiBaseUrl] : apiBaseCandidates();

  for (const baseUrl of candidates) {
    try {
      const headers = new Headers(init?.headers);
      if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
      const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
      if (response.ok || (response.status < 500 && response.status !== 404 && response.status !== 405)) {
        resolvedApiBaseUrl = baseUrl;
        return response;
      }
      lastError = new Error(`Request failed with ${response.status}`);
    } catch (error) {
      lastError = error;
    }
  }

  if (resolvedApiBaseUrl) {
    resolvedApiBaseUrl = null;
    return requestWithFallback(path, init);
  }

  if (lastError instanceof Error) throw lastError;
  throw new Error("API server is unavailable");
}

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item?.msg ?? String(item)).join(", ")
      : typeof detail === "object" && detail !== null
        ? detail.msg ?? JSON.stringify(detail)
        : detail;
    throw new Error(message ?? `Request failed with ${response.status}`);
  }
  return data as T;
}
