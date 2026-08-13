/**
 * Live workflow event protocol — mirrors backend/app/services/events.py.
 * Every event carries a per-idea monotonic `seq` (dedup after reconnect)
 * and epoch `ts`.
 */

export type PhaseKey = "research" | "validate" | "plan" | "build" | "simulate";
export type PhaseStatus = "pending" | "active" | "done";
export type AgentKey =
  | "market_analyst"
  | "tech_architect"
  | "product_manager"
  | "growth_strategist"
  | "financial_analyst"
  | "operations_manager"
  | "legal_advisor";
export type AgentStatus = "idle" | "thinking" | "complete" | "error";
export type LogLevel = "info" | "success" | "warn" | "error";

interface BaseEvent {
  v?: number;
  idea_id?: string;
  seq?: number;
  ts?: number;
}

export type WorkflowEvent = BaseEvent &
  (
    | { type: "snapshot"; data: { events: WorkflowEvent[] } }
    | { type: "ping"; data?: never }
    | { type: "status"; data: { status: string; title?: string } }
    | { type: "phase"; data: { phase: PhaseKey; status: "started" | "completed"; iteration?: number } }
    | { type: "agent"; data: { agent: AgentKey; status: Exclude<AgentStatus, "idle">; detail?: string; duration_ms?: number } }
    | { type: "log"; data: { message: string; agent?: AgentKey; level: LogLevel } }
    | { type: "quality"; data: { score: number; threshold: number; passed: boolean; iteration: number; scores: Record<string, number> } }
    | { type: "sim"; data: { speaker: string; role: string; content: string } }
    | { type: "progress"; data: { node: string; progress: number; status: string } }
    | { type: "complete"; data: { outcome: string | null; funding_offered?: number | null; valuation?: number | null; quality: number; iterations: number } }
    | { type: "error"; data: { message: string } }
  );

/* ── Display registries ─────────────────────────────────────────── */

export const PHASES: { key: PhaseKey; label: string }[] = [
  { key: "research", label: "Research" },
  { key: "validate", label: "Quality Gate" },
  { key: "plan", label: "Plan" },
  { key: "build", label: "Build" },
  { key: "simulate", label: "Simulation" },
];

export const AGENTS: { key: AgentKey; name: string; role: string; phase: PhaseKey }[] = [
  { key: "market_analyst", name: "Market Analyst", role: "TAM · Competitors · Trends", phase: "research" },
  { key: "tech_architect", name: "Tech Architect", role: "Stack · Architecture · MVP", phase: "research" },
  { key: "product_manager", name: "Product Manager", role: "Scope · Stories · Wireframes", phase: "research" },
  { key: "growth_strategist", name: "Growth Strategist", role: "GTM · Pricing · Acquisition", phase: "plan" },
  { key: "financial_analyst", name: "Financial Analyst", role: "Unit Economics · Runway", phase: "plan" },
  { key: "operations_manager", name: "Operations Manager", role: "Hiring · Logistics · SOPs", phase: "plan" },
  { key: "legal_advisor", name: "Legal Advisor", role: "IP · Compliance · Structure", phase: "plan" },
];
