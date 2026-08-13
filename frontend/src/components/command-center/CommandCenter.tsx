"use client";

/**
 * CommandCenter — live LangGraph workflow terminal.
 *
 * Aesthetic contract ("Humane"):
 *   - matte black surfaces, hairline borders, platinum type
 *   - light is semantic: a soft breathing glow ONLY on a thinking agent
 *   - motion is sub-perceptual: 4-6px fades, no springs, no bounces
 *
 * This is the only Client Component in the live view — it owns the
 * WebSocket via useWorkflowSocket. Everything above it renders on the server.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useWorkflowSocket, LogLine } from "@/hooks/useWorkflowSocket";
import { AGENTS, PHASES, AgentStatus, PhaseStatus } from "@/lib/workflow-events";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

/* ── Formatting ─────────────────────────────────────────────────── */

const money = (n?: number | null) =>
  n == null ? "—" : Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(n);

const clock = (ts: number) =>
  new Date(ts * 1000).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

function useElapsed(firstTs: number | null, running: boolean, lastTs: number | null) {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(id);
  }, [running]);
  if (!firstTs) return "00:00";
  const end = running ? now : lastTs ?? now;
  const s = Math.max(0, Math.floor(end - firstTs));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/* ── Atoms ──────────────────────────────────────────────────────── */

function ConnectionDot({ state }: { state: "connecting" | "open" | "closed" }) {
  const tone = state === "open" ? "bg-affirm" : state === "connecting" ? "bg-caution" : "bg-alert";
  return (
    <span className="flex items-center gap-2">
      <span className={`h-1.5 w-1.5 rounded-full ${tone} ${state !== "closed" ? "animate-pulse" : ""}`} />
      <span className="label-caps">{state === "open" ? "Live" : state === "connecting" ? "Linking" : "Offline"}</span>
    </span>
  );
}

function PhaseNode({ label, status, isCurrent }: { label: string; status: PhaseStatus; isCurrent: boolean }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={[
          "h-2.5 w-2.5 rounded-full border transition-colors duration-500",
          status === "done"
            ? "border-porcelain bg-porcelain"
            : status === "active"
              ? "border-signal bg-transparent glow-thinking"
              : "border-steel bg-transparent",
        ].join(" ")}
      />
      <span
        className={[
          "text-[11px] tracking-[0.12em] uppercase transition-colors duration-500",
          isCurrent ? "text-porcelain" : status === "done" ? "text-fog" : "text-smoke",
        ].join(" ")}
      >
        {label}
      </span>
    </div>
  );
}

function AgentRow({
  name,
  role,
  status,
  durationMs,
}: {
  name: string;
  role: string;
  status: AgentStatus;
  durationMs?: number;
}) {
  return (
    <div
      className={[
        "flex items-center justify-between rounded-md border px-4 py-3 transition-colors duration-500",
        status === "thinking" ? "border-transparent glow-thinking bg-graphite" : "border-hairline bg-carbon",
      ].join(" ")}
    >
      <div className="min-w-0">
        <p className={`text-[13px] font-medium tracking-tight ${status === "idle" ? "text-fog" : "text-porcelain"}`}>{name}</p>
        <p className="mt-0.5 truncate text-[11px] text-smoke">{role}</p>
      </div>
      <div className="ml-4 shrink-0 text-right">
        {status === "thinking" && (
          <span className="typing-indicator" aria-label="thinking">
            <span /><span /><span />
          </span>
        )}
        {status === "complete" && (
          <span className="font-mono text-[11px] text-affirm">
            ✓{durationMs ? ` ${(durationMs / 1000).toFixed(1)}s` : ""}
          </span>
        )}
        {status === "error" && <span className="font-mono text-[11px] text-alert">✕</span>}
        {status === "idle" && <span className="font-mono text-[11px] text-steel">·</span>}
      </div>
    </div>
  );
}

const LEVEL_TONE: Record<LogLine["level"], string> = {
  info: "text-fog",
  success: "text-affirm",
  warn: "text-caution",
  error: "text-alert",
};

function TerminalLine({ line }: { line: LogLine }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE }}
      className="flex gap-3 whitespace-pre-wrap py-[3px] text-[12.5px] leading-relaxed"
    >
      <span className="shrink-0 font-mono text-smoke/70">{clock(line.ts)}</span>
      <span className={`font-mono ${LEVEL_TONE[line.level]}`}>{line.message}</span>
    </motion.div>
  );
}

/* ── Main component ─────────────────────────────────────────────── */

export function CommandCenter({ ideaId }: { ideaId: string }) {
  const s = useWorkflowSocket(ideaId);
  const elapsed = useElapsed(s.firstTs, s.running, s.lastTs);
  const logRef = useRef<HTMLDivElement>(null);

  // Terminal autoscroll — only if the user is already at the bottom
  useEffect(() => {
    const el = logRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (nearBottom) el.scrollTop = el.scrollHeight;
  }, [s.logs.length, s.transcript.length]);

  const thinkingCount = useMemo(
    () => Object.values(s.agents).filter((a) => a.status === "thinking").length,
    [s.agents],
  );

  return (
    <div className="min-h-screen bg-void text-porcelain">
      <div className="mx-auto max-w-[1440px] px-8 py-8">
        {/* ── Header ──────────────────────────────────────────── */}
        <header className="flex items-end justify-between pb-8">
          <div>
            <p className="label-caps">Incubation · {ideaId.slice(0, 8)}</p>
            <h1 className="mt-2 text-[22px] font-medium tracking-tight text-signal">
              {s.title ?? "Venture Workflow"}
            </h1>
          </div>
          <div className="flex items-center gap-8">
            {s.iteration > 1 && (
              <span className="label-caps">Pass {s.iteration}</span>
            )}
            <span className="font-mono text-[13px] tabular-nums text-fog">{elapsed}</span>
            <ConnectionDot state={s.connection} />
          </div>
        </header>

        {/* ── Pipeline rail ───────────────────────────────────── */}
        <section className="hairline glass-panel rounded-lg px-10 py-6">
          <div className="relative flex items-start justify-between">
            <div className="absolute left-4 right-4 top-[5px] h-px bg-white/[0.07]" aria-hidden />
            <motion.div
              className="absolute left-4 top-[5px] h-px bg-porcelain/60"
              animate={{ width: `${Math.max(0, s.progress - 4)}%` }}
              transition={{ duration: 0.8, ease: EASE }}
              aria-hidden
            />
            {PHASES.map((p) => (
              <div key={p.key} className="relative z-10">
                <PhaseNode label={p.label} status={s.phases[p.key]} isCurrent={s.currentPhase === p.key} />
              </div>
            ))}
          </div>

          {/* Quality gate readout */}
          <AnimatePresence>
            {s.quality && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.5, ease: EASE }}
                className="mt-6 hairline-t pt-5"
              >
                <div className="flex items-center justify-between">
                  <span className="label-caps">Quality Gate · Pass {s.quality.iteration}</span>
                  <span className={`font-mono text-[12px] tabular-nums ${s.quality.passed ? "text-affirm" : "text-caution"}`}>
                    {s.quality.score.toFixed(2)} / {s.quality.threshold.toFixed(2)} · {s.quality.passed ? "PASSED" : "RETRY"}
                  </span>
                </div>
                <div className="relative mt-3 h-[2px] w-full overflow-hidden rounded-full bg-white/[0.07]">
                  <motion.div
                    className={`h-full ${s.quality.passed ? "bg-affirm" : "bg-caution"}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${s.quality.score * 100}%` }}
                    transition={{ duration: 0.9, ease: EASE }}
                  />
                  <div
                    className="absolute top-[-2px] h-[6px] w-px bg-smoke"
                    style={{ left: `${s.quality.threshold * 100}%` }}
                    title={`Threshold ${s.quality.threshold}`}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* ── Body grid ───────────────────────────────────────── */}
        <div className="mt-6 grid grid-cols-12 gap-6">
          {/* Agents */}
          <aside className="col-span-12 lg:col-span-4">
            <div className="mb-3 flex items-center justify-between px-1">
              <span className="label-caps">Agents</span>
              <span className="font-mono text-[11px] text-smoke">
                {thinkingCount > 0 ? `${thinkingCount} active` : "standing by"}
              </span>
            </div>
            <div className="flex flex-col gap-2">
              {AGENTS.map((a) => (
                <AgentRow
                  key={a.key}
                  name={a.name}
                  role={a.role}
                  status={s.agents[a.key].status}
                  durationMs={s.agents[a.key].durationMs}
                />
              ))}
            </div>

            {/* Verdict */}
            <AnimatePresence>
              {s.result && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, ease: EASE }}
                  className="hairline mt-6 rounded-lg bg-graphite p-5"
                >
                  <p className="label-caps">Verdict</p>
                  <p className="mt-2 text-[20px] font-medium tracking-tight text-signal">
                    {(s.result.outcome ?? "undetermined").toUpperCase()}
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-[11px] text-smoke">Funding</p>
                      <p className="mt-1 font-mono text-[14px] tabular-nums text-porcelain">{money(s.result.fundingOffered)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] text-smoke">Valuation</p>
                      <p className="mt-1 font-mono text-[14px] tabular-nums text-porcelain">{money(s.result.valuation)}</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {s.error && (
              <div className="hairline mt-6 rounded-lg bg-graphite p-5">
                <p className="label-caps text-alert">Workflow Error</p>
                <p className="mt-2 text-[12.5px] leading-relaxed text-fog">{s.error}</p>
              </div>
            )}
          </aside>

          {/* Terminal */}
          <main className="col-span-12 lg:col-span-8">
            <div className="mb-3 flex items-center justify-between px-1">
              <span className="label-caps">Execution Stream</span>
              <span className="font-mono text-[11px] text-smoke">{s.logs.length} events</span>
            </div>
            <div className="hairline glass-panel flex h-[560px] flex-col overflow-hidden rounded-lg">
              <div ref={logRef} className="flex-1 overflow-y-auto px-5 py-4">
                {s.logs.length === 0 && (
                  <p className="font-mono text-[12.5px] text-smoke">
                    Awaiting workflow{s.connection === "open" ? "" : " — connecting"}…
                  </p>
                )}
                {s.logs.map((line) => (
                  <TerminalLine key={line.seq} line={line} />
                ))}

                {/* Investor room — streamed pitch transcript */}
                {s.transcript.length > 0 && (
                  <div className="mt-6 hairline-t pt-5">
                    <p className="label-caps mb-4">Investor Room</p>
                    {s.transcript.map((turn, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, ease: EASE, delay: Math.min(i * 0.05, 0.4) }}
                        className="mb-4"
                      >
                        <p className="text-[11px] tracking-[0.1em] uppercase text-smoke">
                          {turn.speaker}
                          {turn.role ? <span className="text-steel"> · {turn.role}</span> : null}
                        </p>
                        <p className="mt-1 max-w-[64ch] text-[13px] leading-relaxed text-fog">{turn.content}</p>
                      </motion.div>
                    ))}
                  </div>
                )}

                {s.running && (
                  <span className="mt-1 inline-block h-[14px] w-[7px] animate-caret bg-porcelain/70 align-middle" aria-hidden />
                )}
              </div>

              {/* Status footer */}
              <div className="hairline-t flex items-center justify-between px-5 py-3">
                <span className="font-mono text-[11px] text-smoke">
                  {s.running
                    ? `${s.currentPhase ?? "initializing"} · ${s.progress}%`
                    : s.result
                      ? "workflow complete"
                      : s.error
                        ? "workflow failed"
                        : "idle"}
                </span>
                <div className="progress-bar w-40">
                  <div className="progress-bar-fill" style={{ width: `${s.progress}%` }} />
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
