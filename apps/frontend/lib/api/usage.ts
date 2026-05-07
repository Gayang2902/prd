import { apiFetch } from './client';

export interface CostSummary {
  total_sessions: number;
  total_tokens: number;
  total_cost: string;
}

export interface CostByProject {
  project_id: string;
  sessions: number;
  tokens: number;
  cost: string;
}

export interface CostByAgent {
  model_version: string;
  sessions: number;
  tokens: number;
  cost: string;
}

export interface DailyCost {
  date: string;
  sessions: number;
  tokens: number;
  cost: string;
}

function dateParams(since?: string, until?: string): string {
  const q = new URLSearchParams();
  if (since) q.set('since', since);
  if (until) q.set('until', until);
  const qs = q.toString();
  return qs ? `?${qs}` : '';
}

export function fetchCostSummary(since?: string, until?: string): Promise<CostSummary> {
  return apiFetch<CostSummary>(`/usage/cost${dateParams(since, until)}`);
}

export function fetchCostByProject(since?: string, until?: string): Promise<CostByProject[]> {
  return apiFetch<CostByProject[]>(`/usage/by-project${dateParams(since, until)}`);
}

export function fetchCostByAgent(since?: string, until?: string): Promise<CostByAgent[]> {
  return apiFetch<CostByAgent[]>(`/usage/by-agent${dateParams(since, until)}`);
}

export function fetchDailyCost(since?: string, until?: string): Promise<DailyCost[]> {
  return apiFetch<DailyCost[]>(`/usage/daily${dateParams(since, until)}`);
}
