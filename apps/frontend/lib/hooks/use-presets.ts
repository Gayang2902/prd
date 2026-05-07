"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createPreset,
  deletePreset,
  fetchPresets,
  updatePreset,
  type PresetCreate,
  type PresetUpdate,
} from "../api/presets";

export function usePresets(agentId?: string) {
  return useQuery({
    queryKey: ["presets", agentId],
    queryFn: () => fetchPresets(agentId),
  });
}

export function useCreatePreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PresetCreate) => createPreset(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["presets"] }),
  });
}

export function useUpdatePreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PresetUpdate }) =>
      updatePreset(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["presets"] }),
  });
}

export function useDeletePreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deletePreset(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["presets"] }),
  });
}
