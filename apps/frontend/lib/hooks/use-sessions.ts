'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  cancelSession,
  createSession,
  fetchSession,
  fetchSessions,
  type Session,
  type SessionCreate,
} from '../api/sessions';

export function useSessions(projectId: string) {
  return useQuery({
    queryKey: ['sessions', projectId],
    queryFn: () => fetchSessions(projectId),
  });
}

export function useSession(sessionId: string) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchSession(sessionId),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (state === 'completed' || state === 'failed' || state === 'canceled') return false;
      return 3000;
    },
  });
}

export function useCreateSession(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SessionCreate) => createSession(projectId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions', projectId] }),
  });
}

export function useCancelSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => cancelSession(sessionId),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['sessions'] });
      qc.invalidateQueries({ queryKey: ['session', data.id] });
    },
  });
}
