"use client";

/**
 * useWorkflowSocket — the ONLY client-side stateful boundary for the
 * live dashboard. Everything above it stays a Server Component.
 *
 * - Connects to  ws(s)://API/ws/ideas/{id}?token=<jwt>
 * - Applies the snapshot replay, then folds live events into a reducer
 * - De-dupes via monotonic `seq`, reconnects with capped backoff
 */

import { useEffect, useReducer, useRef } from "react";
import {
  AGENTS,
  AgentKey,
  AgentStatus,
  LogLevel,
  PHASES,
  PhaseKey,
  PhaseStatus,
  WorkflowEvent,
} from "@/lib/workflow-events";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const WS_BASE = API_BASE.replace(/^http/, "ws");
const MAX_LOGS = 400;

export interface LogLine {
  seq: number;
  ts: number;
  level: LogLevel;
  agent?: AgentKey;
  message: string;
}

export interface SimTurn {
  speaker: string;
  role: string;
  content: string;
}

export interface WorkflowUiState {
  connection: "connecting" | "open" | "closed";
  running: boolean;
  title: string | null;
  phases: Record<PhaseKey, PhaseStatus>;
  currentPhase: PhaseKey | null;
  iteration: number;
  agents: Record<AgentKey, { status: AgentStatus; detail?: string; durationMs?: number }>;
  logs: LogLine[];
  quality: { score: number; threshold: number; passed: boolean; iteration: number } | null;
  transcript: SimTurn[];
  progress: number;
  result: { outcome: string | null; fundingOffered?: number | null; valuation?: number | null; quality: number } | null;
  error: string | null;
  firstTs: number | null;
  lastTs: number | null;
  lastSeq: number;
}

const initialState = (): WorkflowUiState => ({
  connection: "connecting",
  running: false,
  title: null,
  phases: Object.fromEntries(PHASES.map((p) => [p.key, "pending"])) as Record<PhaseKey, PhaseStatus>,
  currentPhase: null,
  iteration: 0,
  agents: Object.fromEntries(AGENTS.map((a) => [a.key, { status: "idle" }])) as WorkflowUiState["agents"],
  logs: [],
  quality: null,
  transcript: [],
  progress: 0,
  result: null,
  error: null,
  firstTs: null,
  lastTs: null,
  lastSeq: 0,
});

type Action =
  | { kind: "event"; event: WorkflowEvent }
  | { kind: "snapshot"; events: WorkflowEvent[] }
  | { kind: "connection"; value: WorkflowUiState["connection"] };

function applyEvent(state: WorkflowUiState, e: WorkflowEvent): WorkflowUiState {
  if (e.type === "ping" || e.type === "snapshot") return state;
  const seq = e.seq ?? 0;
  if (seq !== 0 && seq <= state.lastSeq) return state; // replayed duplicate
  const ts = e.ts ?? Date.now() / 1000;

  const next: WorkflowUiState = {
    ...state,
    lastSeq: Math.max(state.lastSeq, seq),
    firstTs: state.firstTs ?? ts,
    lastTs: ts,
  };

  switch (e.type) {
    case "status":
      next.running = e.data.status === "running";
      next.title = e.data.title || state.title;
      if (e.data.status === "running") {
        // fresh run — reset derived state but keep connection
        return { ...initialState(), connection: state.connection, running: true, title: e.data.title || null, firstTs: ts, lastTs: ts, lastSeq: seq };
      }
      return next;

    case "phase": {
      const phases = { ...state.phases };
      if (e.data.status === "started") {
        phases[e.data.phase] = "active";
        next.currentPhase = e.data.phase;
        // A re-entered research phase (quality loop) re-arms the gate
        if (e.data.phase === "research" && state.phases.research === "done") {
          phases.validate = "pending";
        }
      } else {
        phases[e.data.phase] = "done";
      }
      if (e.data.iteration) next.iteration = e.data.iteration;
      next.phases = phases;
      return next;
    }

    case "agent": {
      const status = e.data.status as AgentStatus;
      next.agents = {
        ...state.agents,
        [e.data.agent]: { status, detail: e.data.detail, durationMs: e.data.duration_ms },
      };
      return next;
    }

    case "log": {
      const line: LogLine = { seq, ts, level: e.data.level, agent: e.data.agent, message: e.data.message };
      const logs = [...state.logs, line];
      next.logs = logs.length > MAX_LOGS ? logs.slice(-MAX_LOGS) : logs;
      return next;
    }

    case "quality":
      next.quality = e.data;
      return next;

    case "sim":
      next.transcript = [...state.transcript, e.data];
      return next;

    case "progress":
      next.progress = e.data.progress;
      return next;

    case "complete":
      next.running = false;
      next.progress = 100;
      next.result = {
        outcome: e.data.outcome,
        fundingOffered: e.data.funding_offered,
        valuation: e.data.valuation,
        quality: e.data.quality,
      };
      return next;

    case "error":
      next.running = false;
      next.error = e.data.message;
      return next;

    default:
      return state;
  }
}

function reducer(state: WorkflowUiState, action: Action): WorkflowUiState {
  switch (action.kind) {
    case "connection":
      return { ...state, connection: action.value };
    case "snapshot": {
      let s = { ...initialState(), connection: state.connection };
      for (const e of action.events) s = applyEvent(s, e);
      return s;
    }
    case "event":
      return applyEvent(state, action.event);
  }
}

export function useWorkflowSocket(ideaId: string): WorkflowUiState {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  const retryRef = useRef(0);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let retryTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const url = `${WS_BASE}/ws/ideas/${ideaId}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
      dispatch({ kind: "connection", value: "connecting" });
      ws = new WebSocket(url);

      ws.onopen = () => {
        retryRef.current = 0;
        dispatch({ kind: "connection", value: "open" });
      };

      ws.onmessage = (msg) => {
        let event: WorkflowEvent;
        try {
          event = JSON.parse(msg.data);
        } catch {
          return;
        }
        if (event.type === "ping") return;
        if (event.type === "snapshot") {
          dispatch({ kind: "snapshot", events: event.data.events });
        } else {
          dispatch({ kind: "event", event });
        }
      };

      ws.onclose = () => {
        if (closed) return;
        dispatch({ kind: "connection", value: "closed" });
        const delay = Math.min(10_000, 500 * 2 ** retryRef.current++);
        retryTimer = setTimeout(connect, delay);
      };

      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, [ideaId]);

  return state;
}
