export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8787";

export type SetupStatus = {
  ready: boolean;
  next: string;
  selected_property: string | null;
  steps: Record<string, boolean>;
  ollama: { available: boolean; models: string[]; error?: string };
};

export type PropertyItem = { site_url: string; permission: string };

export type Opportunity = {
  id: string;
  kind: "low_ctr" | "striking_distance" | "decay" | "cannibalization";
  score: number;
  query: string;
  page: string;
  pages?: string[];
  metrics: Record<string, number>;
};

export type Audit = {
  audit_id: number;
  site_url: string;
  period: { start: string; end: string; days: number };
  previous_period: { start: string; end: string };
  summary: {
    current: { clicks: number; impressions: number; ctr: number; position: number };
    previous: { clicks: number; impressions: number; ctr: number; position: number };
    delta: { clicks: number | null; impressions: number | null; ctr: number | null; position: number | null };
  };
  trend: Array<{ date: string; clicks: number; impressions: number; ctr: number; position: number }>;
  opportunities: Opportunity[];
  rows_analyzed: number;
  data_note?: string;
  created_at?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {}
    throw new Error(message);
  }
  return response.json();
}

export const api = {
  setup: () => request<SetupStatus>("/api/setup/status"),
  saveCredentials: (credentials: Record<string, unknown>) =>
    request<{ ok: boolean; redirect_uri: string; scope: string }>("/api/google/credentials", {
      method: "POST",
      body: JSON.stringify({ credentials }),
    }),
  properties: () => request<{ items: PropertyItem[] }>("/api/google/properties"),
  selectProperty: (site_url: string) =>
    request<{ site_url: string }>("/api/google/property", {
      method: "POST",
      body: JSON.stringify({ site_url }),
    }),
  latestAudit: () => request<Audit>("/api/audits/latest"),
  importAudit: () =>
    request<Audit>("/api/import/search-console", {
      method: "POST",
      body: JSON.stringify({ days: 28, row_limit: 25000, max_rows: 50000 }),
    }),
  inspectUrl: (url: string, language: "en-US" | "fa-IR") =>
    request<Record<string, unknown>>("/api/url-inspection", {
      method: "POST",
      body: JSON.stringify({ url, language }),
    }),
  aiStatus: () => request<{ available: boolean; models: string[]; error?: string }>("/api/ai/status"),
  explain: (opportunity: Opportunity, language: "en" | "fa", model?: string) =>
    request<{ summary: string; why_it_matters: string; actions: string[]; model: string }>("/api/ai/explain", {
      method: "POST",
      body: JSON.stringify({ opportunity, language, model }),
    }),
  disconnect: () => request<{ ok: boolean }>("/api/google/connection", { method: "DELETE" }),
};
