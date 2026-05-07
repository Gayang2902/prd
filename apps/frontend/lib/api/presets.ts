import { apiFetch } from "./client";

export interface Preset {
  id: string;
  name: string;
  agent_id: string;
  version_sha: string;
  prompt_template: string;
  ruleset: Record<string, unknown>;
  timeout_seconds: number;
  max_retries: number;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
}

export interface PresetCreate {
  name: string;
  agent_id: string;
  version_sha: string;
  prompt_template?: string;
  ruleset?: Record<string, unknown>;
  timeout_seconds?: number;
  max_retries?: number;
  is_shared?: boolean;
}

export interface PresetUpdate {
  name?: string;
  prompt_template?: string;
  ruleset?: Record<string, unknown>;
  timeout_seconds?: number;
  max_retries?: number;
  is_shared?: boolean;
}

export function fetchPresets(agentId?: string): Promise<Preset[]> {
  const qs = agentId ? `?agent_id=${agentId}` : "";
  return apiFetch<Preset[]>(`/presets${qs}`);
}

export function fetchPreset(presetId: string): Promise<Preset> {
  return apiFetch<Preset>(`/presets/${presetId}`);
}

export function createPreset(data: PresetCreate): Promise<Preset> {
  return apiFetch<Preset>("/presets", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updatePreset(
  presetId: string,
  data: PresetUpdate,
): Promise<Preset> {
  return apiFetch<Preset>(`/presets/${presetId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deletePreset(presetId: string): Promise<void> {
  return apiFetch(`/presets/${presetId}`, { method: "DELETE" });
}
