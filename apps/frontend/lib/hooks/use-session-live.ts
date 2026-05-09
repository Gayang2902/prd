"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

export interface AgentEvent {
  type: "agent_event";
  event: string;
  phase: string;
  turn?: number;
  tool_calls?: string[];
  num_turns?: number;
  cost_usd?: number;
  duration_ms?: number;
  message?: string;
  session_type?: string;
  ts: number;
}

export function useSessionLive(sessionId: string) {
  const qc = useQueryClient();
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  const eventsRef = useRef(agentEvents);
  eventsRef.current = agentEvents;

  useEffect(() => {
    setAgentEvents([]);
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

      if (event.type === "agent_event") {
        const ae: AgentEvent = { ...event, ts: Date.now() };
        setAgentEvents((prev) => [...prev.slice(-200), ae]);

        if (event.event === "phase_done") {
          qc.invalidateQueries({ queryKey: ["session", sessionId] });
        }
      }
    };

    return () => ws.close();
  }, [sessionId, qc]);

  return { agentEvents };
}
