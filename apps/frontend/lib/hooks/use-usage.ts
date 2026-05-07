"use client";

import { useQuery } from "@tanstack/react-query";
import {
  fetchCostByAgent,
  fetchCostByProject,
  fetchCostSummary,
  fetchDailyCost,
} from "@/lib/api/usage";

export function useCostSummary(since?: string, until?: string) {
  return useQuery({
    queryKey: ["cost-summary", since, until],
    queryFn: () => fetchCostSummary(since, until),
  });
}

export function useCostByProject(since?: string, until?: string) {
  return useQuery({
    queryKey: ["cost-by-project", since, until],
    queryFn: () => fetchCostByProject(since, until),
  });
}

export function useCostByAgent(since?: string, until?: string) {
  return useQuery({
    queryKey: ["cost-by-agent", since, until],
    queryFn: () => fetchCostByAgent(since, until),
  });
}

export function useDailyCost(since?: string, until?: string) {
  return useQuery({
    queryKey: ["daily-cost", since, until],
    queryFn: () => fetchDailyCost(since, until),
  });
}
