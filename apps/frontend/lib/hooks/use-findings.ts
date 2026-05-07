'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchFindings, updateFindingStatus, type Finding } from '../api/findings';

export function useFindings(sessionId: string, params?: { severity?: string }) {
  return useQuery({
    queryKey: ['findings', sessionId, params],
    queryFn: () => fetchFindings(sessionId, params),
  });
}

export function useUpdateFindingStatus(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ findingId, status, reason }: { findingId: string; status: string; reason?: string }) =>
      updateFindingStatus(findingId, { status, reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['findings', sessionId] }),
  });
}
