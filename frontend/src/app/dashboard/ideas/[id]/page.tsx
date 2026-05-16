"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import styles from "./detail.module.css";
import { ideasApi, agentsApi, reportsApi, type Idea, type AgentActivity, type Report } from "@/lib/api";

const PHASES = [
  { id: "research", label: "Research", icon: "🔍" },
  { id: "validate", label: "Validate", icon: "✅" },
  { id: "plan", label: "Plan", icon: "📋" },
  { id: "build", label: "Build", icon: "🏗️" },
  { id: "simulate", label: "Simulate", icon: "🎯" },
];

export default function IdeaDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [idea, setIdea] = useState<Idea | null>(null);
  const [activities, setActivities] = useState<AgentActivity[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [ideaData, activitiesData, reportsData] = await Promise.allSettled([
          ideasApi.get(id),
          agentsApi.getActivities(id),
          reportsApi.listForIdea(id),
        ]);

        if (ideaData.status === "fulfilled") setIdea(ideaData.value);
        else setError("Idea not found");

        if (activitiesData.status === "fulfilled") {
          setActivities(Array.isArray(activitiesData.value) ? activitiesData.value : []);
        }
        if (reportsData.status === "fulfilled") {
          setReports(Array.isArray(reportsData.value) ? reportsData.value : []);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load idea");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const getPhaseStatus = (phaseId: string) => {
    if (!idea) return "pending";
    const phaseOrder = ["research", "validate", "plan", "build", "simulate"];
    const statusMap: Record<string, string> = {
      draft: "research", submitted: "research", researching: "research",
      validating: "validate", planning: "plan", simulating: "simulate",
      completed: "simulate", failed: "research",
    };
    const currentPhase = statusMap[idea.status] || "research";
    const currentIdx = phaseOrder.indexOf(currentPhase);
    const thisIdx = phaseOrder.indexOf(phaseId);
    if (idea.status === "completed") return "completed";
    if (thisIdx < currentIdx) return "completed";
    if (thisIdx === currentIdx) return "active";
    return "pending";
  };

  if (loading) {
    return (
      <div className="animate-fade-in">
        <div className="skeleton" style={{ height: 32, width: "40%", marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 120, width: "100%", marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 200, width: "100%" }} />
      </div>
    );
  }

  if (error || !idea) {
    return (
      <div className="animate-fade-in" style={{ textAlign: "center", padding: "var(--space-16)" }}>
        <h2>⚠️ {error || "Idea not found"}</h2>
        <Link href="/dashboard/ideas" className="btn btn-secondary" style={{ marginTop: 16 }}>← Back to Ideas</Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className={styles.header}>
        <div>
          <Link href="/dashboard/ideas" className={styles.backLink}>← Back to Ideas</Link>
          <h1 className={styles.title}>{idea.title}</h1>
          <div className={styles.meta}>
            <span className={`badge badge-${idea.status === "completed" ? "success" : idea.status === "failed" ? "error" : "info"}`}>{idea.status}</span>
            {idea.industry && <span className="badge badge-accent">{idea.industry}</span>}
            <span className={styles.date}>Created {new Date(idea.created_at).toLocaleDateString()}</span>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button className="btn btn-primary btn-sm" onClick={async () => {
            try { await ideasApi.launch(idea.id); window.location.reload(); } catch {}
          }}>🚀 Relaunch</button>
        </div>
      </div>

      {/* Progress Timeline */}
      <div className={`${styles.timeline} glass-card`}>
        <h3 className={styles.timelineTitle}>Incubation Progress — {idea.progress}%</h3>
        <div className={styles.phases}>
          {PHASES.map((phase, i) => (
            <div key={phase.id} className={`${styles.phase} ${styles[`phase_${getPhaseStatus(phase.id)}`]}`}>
              <div className={styles.phaseIcon}>{phase.icon}</div>
              <div className={styles.phaseLabel}>{phase.label}</div>
              {i < PHASES.length - 1 && <div className={styles.phaseConnector} />}
            </div>
          ))}
        </div>
        <div className="progress-bar" style={{ marginTop: "var(--space-4)" }}>
          <div className="progress-bar-fill" style={{ width: `${idea.progress}%` }} />
        </div>
      </div>

      {/* Content Grid */}
      <div className={styles.contentGrid}>
        <div className={`${styles.descCard} glass-card`}>
          <h3>Description</h3>
          <p>{idea.description}</p>
          {idea.problem_statement && (<><h4>Problem Statement</h4><p>{idea.problem_statement}</p></>)}
          {idea.proposed_solution && (<><h4>Proposed Solution</h4><p>{idea.proposed_solution}</p></>)}
          {idea.target_market && (<><h4>Target Market</h4><p>{idea.target_market}</p></>)}
        </div>

        <div className={`${styles.agentsCard} glass-card`}>
          <h3>Agent Activity ({activities.length})</h3>
          {activities.length > 0 ? (
            <div className={styles.agentList}>
              {activities.map((a) => (
                <div key={a.id} className={styles.agentRow}>
                  <span>{a.agent_name} — {a.action}</span>
                  <span className={`badge badge-${a.status === "completed" ? "success" : a.status === "running" ? "info" : "warning"}`}>
                    {a.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)", fontSize: "var(--fs-sm)" }}>
              No agent activity yet. Launch the incubation to start.
            </p>
          )}

          {reports.length > 0 && (
            <>
              <h3 style={{ marginTop: "var(--space-5)" }}>Reports ({reports.length})</h3>
              <div className={styles.agentList}>
                {reports.map((r) => (
                  <div key={r.id} className={styles.agentRow}>
                    <span>{r.title}</span>
                    <span className="badge badge-accent">{r.report_type}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
