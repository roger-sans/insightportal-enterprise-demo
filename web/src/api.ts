export type DomainId = 'finance' | 'commercial' | 'operations' | 'people';
export type Metric = {
  id: string; name: string; unit: 'EUR' | '%' | 'count'; goal: number;
  goal_basis: 'monthly_global' | 'period'; direction: 'up' | 'down';
  definition: string; formula: string; exclusions: string;
};
export type Domain = {
  id: DomainId; name: string; product: string; owner: string; purpose: string; consumer: string;
  table: string; source: string; freshness_hours: number; metrics: Metric[];
};
export type Catalog = {
  contract: { version: string; scenario_as_of: string; sites: { id: string; name: string }[]; domains: Domain[] };
  actors: Record<string, string>;
  years: Record<string, number>;
};
export type Quality = {
  id: DomainId; status: 'current' | 'late' | 'blocked'; checks: Record<string, boolean>;
  rows: number; expected_rows: number; published_at: string | null; through_month: string | null;
  age_hours: number | null; sla_hours: number;
};
export type MetricResult = {
  id: string; value: number | null; previous: number | null; delta: number | null; goal: number | null;
  trend_goal: number | null; trend: { month: string; value: number | null }[]; sites: { id: string; value: number | null }[];
};
export type Dashboard = {
  start: string; end: string; site: string | null; mode: 'local' | 'snowflake'; quality: Quality[]; metrics: MetricResult[];
};
export type BacklogItem = {
  id: number; domain: DomainId; title: string; rationale: string; requester: string;
  kind: 'enhancement' | 'data-contract' | 'quality';
  state: 'submitted' | 'triaged' | 'accepted' | 'released' | 'declined';
  impact: number; urgency: number; effort: number; version: number; score: number;
  history: { id: number; actor: string; action: string; note: string; recorded_at: string }[];
};
export type Adoption = {
  id: DomainId; eligible: number; active: number; returning: number; weeks: number[];
  survey_count: number; survey_average: number; local_feedback: { count: number; average: number | null };
};

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch('/api/v1' + path, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string'
      ? error.detail : error.detail?.[0]?.msg || 'Unable to complete the request.');
  }
  return response.json() as Promise<T>;
}

export function post<T>(path: string, body: unknown) {
  return api<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}
