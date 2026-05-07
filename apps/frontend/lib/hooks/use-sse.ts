'use client';

import { useEffect, useRef, useState } from 'react';

export interface SSEEvent {
  event: string;
  data: string;
  timestamp: number;
}

export function useSSE(url: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!url) return;

    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);

    const handler = (type: string) => (e: MessageEvent) => {
      setEvents((prev) => [...prev, { event: type, data: e.data, timestamp: Date.now() }]);
    };

    source.addEventListener('state', handler('state'));
    source.addEventListener('progress', handler('progress'));
    source.addEventListener('log', handler('log'));
    source.addEventListener('done', (e) => {
      handler('done')(e);
      source.close();
      setConnected(false);
    });

    return () => {
      source.close();
      setConnected(false);
    };
  }, [url]);

  return { events, connected };
}
