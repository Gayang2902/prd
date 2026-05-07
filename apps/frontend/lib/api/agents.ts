import { apiFetch } from './client';

export interface AgentInfo {
  name: string;
  version: string;
  supported_languages: string[];
  max_input_size_bytes: number;
  cost_profile: Record<string, number>;
  description: string;
}

export function fetchAgents(): Promise<Record<string, AgentInfo>> {
  return apiFetch<Record<string, AgentInfo>>('/agents');
}
