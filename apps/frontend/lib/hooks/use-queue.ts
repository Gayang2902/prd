'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchQueue } from '@/lib/api/queue';

export function useQueue(state?: string) {
  return useQuery({
    queryKey: ['queue', state],
    queryFn: () => fetchQueue(state),
    refetchInterval: 5000,
  });
}
