"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createTargetDiscovery,
  createZeroDayHunt,
  fetchHuntingSessions,
  fetchTargetCandidates,
  type HuntingSessionCreate,
} from "../api/hunting";

export function useHuntingSessions(projectId?: string) {
  return useQuery({
    queryKey: ["hunting-sessions", projectId ?? "all"],
    queryFn: () => fetchHuntingSessions(projectId),
    refetchInterval: 5000,
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
      qc.invalidateQueries({ queryKey: ["hunting-sessions"] });
      qc.invalidateQueries({ queryKey: ["sessions", data.project_id] });
    },
  });
}

export function useCreateZeroDayHunt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: HuntingSessionCreate) => createZeroDayHunt(data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["hunting-sessions"] });
      qc.invalidateQueries({ queryKey: ["sessions", data.project_id] });
    },
  });
}
