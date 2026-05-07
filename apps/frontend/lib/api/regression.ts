import { apiFetch } from './client';

export interface RegressionSummary {
  session_id: string;
  commit_sha: string;
  started_at: string;
  new: number;
  recurring: number;
  resolved: number;
  total: number;
}

export function fetchRegressionHistory(projectId: string): Promise<RegressionSummary[]> {
  return apiFetch<RegressionSummary[]>(`/projects/${projectId}/regression-history`);
}
