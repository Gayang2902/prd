'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchRegressionHistory } from '@/lib/api/regression';

export function useRegressionHistory(projectId: string) {
  return useQuery({
    queryKey: ['regression-history', projectId],
    queryFn: () => fetchRegressionHistory(projectId),
  });
}
