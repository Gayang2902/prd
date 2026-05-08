import { apiFetch } from "./client";

export interface Finding {
  id: string;
  session_id: string;
  fingerprint: string;
  file_path: string;
  line_start: number;
  line_end: number;
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  title: string;
  description: string;
  regression_status: "new" | "recurring" | "resolved" | "carried_over";
  extras: Record<string, unknown> | null;
  created_at: string;
}

export interface FindingStatus {
  id: string;
  finding_id: string;
  changed_by: string;
  status: "open" | "confirmed" | "false_positive" | "needs_review";
  reason: string | null;
  changed_at: string;
}

export function fetchFindings(
  sessionId: string,
  params?: { severity?: string },
): Promise<Finding[]> {
  const query = new URLSearchParams();
  if (params?.severity) query.set("severity", params.severity);
  const qs = query.toString();
  return apiFetch<Finding[]>(
    `/sessions/${sessionId}/findings${qs ? `?${qs}` : ""}`,
  );
}

export function updateFindingStatus(
  findingId: string,
  data: { status: string; reason?: string },
): Promise<FindingStatus> {
  return apiFetch<FindingStatus>(`/findings/${findingId}/status`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function fetchFindingTimeline(
  findingId: string,
): Promise<FindingStatus[]> {
  return apiFetch<FindingStatus[]>(`/findings/${findingId}/timeline`);
}
