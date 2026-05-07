'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface SyncEvent {
  type: 'user_joined' | 'user_left' | 'finding_status_changed' | 'comment_added' | 'cursor_moved';
  user_id: string;
  finding_id?: string;
  status?: string;
  content?: string;
}

export function useReviewSync(sessionId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<SyncEvent[]>([]);
  const [activeUsers, setActiveUsers] = useState<string[]>([]);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000';
    const ws = new WebSocket(`${base}/ws/sessions/${sessionId}?user_id=current`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (e) => {
      const event: SyncEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev.slice(-49), event]);

      if (event.type === 'user_joined') {
        setActiveUsers((prev) => [...new Set([...prev, event.user_id])]);
      } else if (event.type === 'user_left') {
        setActiveUsers((prev) => prev.filter((u) => u !== event.user_id));
      }
    };

    return () => ws.close();
  }, [sessionId]);

  const send = useCallback((event: Omit<SyncEvent, 'user_id'>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(event));
    }
  }, []);

  return { connected, events, activeUsers, send };
}
