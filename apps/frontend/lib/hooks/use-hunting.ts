"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createTargetDiscovery,
  createZeroDayHunt,
  fetchTargetCandidates,
  type HuntingSessionCreate,
} from "../api/hunting";
import { fetchSessions } from "../api/sessions";

export function useHuntingSessions(projectId: string) {
  return useQuery({
    queryKey: ["hunting-sessions", projectId],
    queryFn: async () => {
      const sessions = await fetchSessions(projectId);
      return sessions.filter((s) => s.session_type !== "static_analysis");
    },
  });
}

export function useTargetCandidates(sessionId: string) {
  return useQuery({
    queryKey: ["target-candidates", sessionId],
    queryFn: () => fetchTargetCandidates(sessionId),
    enabled: !!sessionId,
  });
}

export function useCreateTargetDiscovery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: HuntingSessionCreate) => createTargetDiscovery(data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["hunting-sessions", data.project_id] });
      qc.invalidateQueries({ queryKey: ["sessions", data.project_id] });
    },
  });
}

export function useCreateZeroDayHunt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: HuntingSessionCreate) => createZeroDayHunt(data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["hunting-sessions", data.project_id] });
      qc.invalidateQueries({ queryKey: ["sessions", data.project_id] });
    },
  });
}
