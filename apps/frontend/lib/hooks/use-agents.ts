"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAgents } from "../api/agents";

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: fetchAgents,
  });
}
