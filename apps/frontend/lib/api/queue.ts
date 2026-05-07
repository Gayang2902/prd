import type { Session } from './sessions';
import { apiFetch } from './client';

export function fetchQueue(state?: string): Promise<Session[]> {
  const query = new URLSearchParams();
  if (state) query.set('state', state);
  const qs = query.toString();
  return apiFetch<Session[]>(`/queue${qs ? `?${qs}` : ''}`);
}
