import { apiFetch } from "./client";

export interface Session {
  id: string;
  project_id: string;
  commit_sha: string;
  agent_id: string;
  preset_id: string;
  model_version: string;
  container_image_sha: string | null;
  state:
    | "queued"
    | "preparing"
    | "running"
    | "post_processing"
    | "completed"
    | "failed"
    | "canceled";
  priority: "urgent" | "normal" | "background";
  started_at: string;
  completed_at: string | null;
  token_usage: number;
  cost: string;
}

export interface SessionCreate {
  branch: string;
  commit_sha?: string | null;
  diff_base_sha?: string | null;
  preset_id: string;
  agent_id: string;
  priority?: string;
}

export function fetchSessions(projectId: string): Promise<Session[]> {
  return apiFetch<Session[]>(`/projects/${projectId}/sessions`);
}

export function fetchSession(sessionId: string): Promise<Session> {
  return apiFetch<Session>(`/sessions/${sessionId}`);
}

export function createSession(
  projectId: string,
  data: SessionCreate,
): Promise<Session> {
  return apiFetch<Session>(`/projects/${projectId}/sessions`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function cancelSession(sessionId: string): Promise<Session> {
  return apiFetch<Session>(`/sessions/${sessionId}/cancel`, { method: "POST" });
}

export function getLogsUrl(sessionId: string): string {
  const base =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/v1";
  return `${base}/sessions/${sessionId}/logs`;
}
