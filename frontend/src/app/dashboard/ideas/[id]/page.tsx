"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import styles from "./detail.module.css";
import { ideasApi, agentsApi, reportsApi, type Idea, type AgentActivity, type Report } from "@/lib/api";
import { FinancialDashboard } from "@/components/FinancialDashboard";

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
  const [isPublishing, setIsPublishing] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function load(isInitial = false) {
      if (isInitial) setLoading(true);
      try {
        const [ideaData, activitiesData, reportsData] = await Promise.allSettled([
          ideasApi.get(id),
          agentsApi.getActivities(id),
          reportsApi.listForIdea(id),
        ]);

        if (!mounted) return;

        if (ideaData.status === "fulfilled") setIdea(ideaData.value);
        else if (isInitial) setError("Idea not found");

        if (activitiesData.status === "fulfilled") {
          setActivities(Array.isArray(activitiesData.value) ? activitiesData.value : []);
        }
        if (reportsData.status === "fulfilled") {
          setReports(Array.isArray(reportsData.value) ? reportsData.value : []);
        }
      } catch (err) {
        if (mounted && isInitial) setError(err instanceof Error ? err.message : "Failed to load idea");
      } finally {
        if (mounted && isInitial) setLoading(false);
      }
    }
    load(true);

    const interval = setInterval(() => {
      load(false);
    }, 3000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
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
            <span className={`badge badge-${idea.status === "completed" ? "success" : idea.status === "failed" ? "error" : "info"}`} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {!['completed', 'failed', 'draft'].includes(idea.status) && (
                <span className="loader" style={{ width: 12, height: 12, borderWidth: 2 }} />
              )}
              {idea.status}
            </span>
            {idea.industry && <span className="badge badge-accent">{idea.industry}</span>}
            <span className={styles.date}>Created {new Date(idea.created_at).toLocaleDateString()}</span>
            {idea.is_public === 1 && idea.public_slug && (
              <a href={`/p/${idea.public_slug}`} target="_blank" rel="noopener noreferrer" className="badge badge-success" style={{ cursor: "pointer", textDecoration: "none" }}>
                🌐 Public Link
              </a>
            )}
          </div>
        </div>
        <div className={styles.headerActions}>
          <button 
            className="btn btn-secondary btn-sm" 
            disabled={isPublishing}
            onClick={async () => {
              try {
                setIsPublishing(true);
                const res = await ideasApi.publish(idea.id);
                const url = `${window.location.origin}/p/${res.public_slug}`;
                await navigator.clipboard.writeText(url);
                alert(`Published! Link copied to clipboard:\n${url}`);
                window.location.reload();
              } catch (e) {
                alert("Failed to publish");
              } finally {
                setIsPublishing(false);
              }
          }}>
            {isPublishing ? "Publishing..." : idea.is_public === 1 ? "🔗 Copy Link" : "🌍 Publish to Web"}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => window.location.href = `/dashboard/ideas/${idea.id}/edit`}>
            ✏️ Edit
          </button>
          <button className="btn btn-primary btn-sm" onClick={async () => {
            try { await ideasApi.launch(idea.id); window.location.reload(); } catch {}
          }}>🚀 Relaunch</button>
          <button 
            className="btn btn-secondary btn-sm" 
            style={{ color: "var(--error)", borderColor: "var(--error-soft)" }}
            onClick={async () => {
              if (confirm("Are you sure you want to delete this idea? This cannot be undone.")) {
                try {
                  await ideasApi.delete(idea.id);
                  window.location.href = "/dashboard/ideas";
                } catch {
                  alert("Failed to delete idea");
                }
              }
          }}>🗑️ Delete</button>
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

      {/* Render Full Reports */}
      <div style={{ marginTop: "var(--space-12)" }}>
        {reports.map(r => (
          <div key={r.id} className="glass-card" style={{ marginBottom: "var(--space-8)" }}>
            <h3 style={{ borderBottom: "1px solid var(--border-color)", paddingBottom: "var(--space-4)", marginBottom: "var(--space-6)" }}>
              {r.title}
            </h3>
            {r.report_type === "financial_projection" && typeof r.content === 'string' ? (
              <FinancialDashboard content={r.content} />
            ) : (
              <div className="prose prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: typeof r.content === 'string' ? r.content : JSON.stringify(r.content) }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
