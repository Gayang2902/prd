import { apiFetch } from "./client";

export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  detail: string | null;
  ip_address: string | null;
  created_at: string;
}

export function fetchAuditLogs(params?: {
  action?: string;
  resource_type?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditLog[]> {
  const q = new URLSearchParams();
  if (params?.action) q.set("action", params.action);
  if (params?.resource_type) q.set("resource_type", params.resource_type);
  if (params?.limit) q.set("limit", String(params.limit));
  if (params?.offset) q.set("offset", String(params.offset));
  const qs = q.toString();
  return apiFetch<AuditLog[]>(`/audit/logs${qs ? `?${qs}` : ""}`);
}
