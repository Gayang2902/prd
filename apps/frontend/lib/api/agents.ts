import { apiFetch } from "./client";

export interface AgentInfo {
  id: string;
  name: string;
  version: string;
  description: string;
}

export function fetchAgents(): Promise<AgentInfo[]> {
  return apiFetch<AgentInfo[]>("/agents");
}
