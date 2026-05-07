"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAuditLogs } from "@/lib/api/audit";

export function useAuditLogs(params?: {
  action?: string;
  resource_type?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ["audit-logs", params],
    queryFn: () => fetchAuditLogs(params),
  });
}
