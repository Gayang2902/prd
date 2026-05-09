"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useSessionLive(sessionId: string) {
  const qc = useQueryClient();

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:18000";
    const ws = new WebSocket(
      `${base}/ws/sessions/${sessionId}?user_id=live`,
    );

    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.type === "phase_updated" || event.type === "state_changed") {
        qc.invalidateQueries({ queryKey: ["session", sessionId] });
        qc.invalidateQueries({ queryKey: ["target-candidates", sessionId] });
        qc.invalidateQueries({ queryKey: ["findings", sessionId] });
      }
    };

    return () => ws.close();
  }, [sessionId, qc]);
}
