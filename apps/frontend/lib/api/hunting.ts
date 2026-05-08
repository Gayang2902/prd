import { apiFetch } from "./client";
import type { Session } from "./sessions";
import type { Finding } from "./findings";

export interface HuntingSessionCreate {
  project_id: string;
  preset_id: string;
  agent_id: string;
  commit_sha?: string | null;
  priority?: string;
  config?: Record<string, unknown>;
}

export interface PhaseUpdate {
  phase: string;
  status: string;
  data?: Record<string, unknown>;
}

export function createTargetDiscovery(
  data: HuntingSessionCreate,
): Promise<Session> {
  return apiFetch<Session>("/hunting/target-discovery", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function createZeroDayHunt(
  data: HuntingSessionCreate,
): Promise<Session> {
  return apiFetch<Session>("/hunting/zero-day", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updatePhase(
  sessionId: string,
  data: PhaseUpdate,
): Promise<Session> {
  return apiFetch<Session>(`/hunting/sessions/${sessionId}/phase`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function fetchTargetCandidates(sessionId: string): Promise<Finding[]> {
  return apiFetch<Finding[]>(`/hunting/sessions/${sessionId}/targets`);
}
