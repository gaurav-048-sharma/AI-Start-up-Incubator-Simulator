"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import styles from "./dashboard.module.css";
import { authApi, ideasApi, analyticsApi, type Idea } from "@/lib/api";

export default function DashboardPage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendStatus, setBackendStatus] = useState<Record<string, boolean>>({});
  const [credits, setCredits] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      try {
        setLoadError(null);
        const [ideasData, analyticsData, healthCheck] = await Promise.all([
          ideasApi.list().catch(() => ({ ideas: [] })),
          analyticsApi.getCredits().catch(() => ({ credits: null })),
          fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/health`).catch(() => null),
        ]);

        if (!mounted) return;
        setIdeas(ideasData.ideas || []);
        setCredits(analyticsData.credits);

        if (healthCheck) {
          const healthData = await healthCheck.json();
          setBackendStatus(healthData.services || {});
        }
      } catch (err) {
        if (mounted) setLoadError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadData();

    return () => {
      mounted = false;
    };
  }, []);

  const totalIdeas = ideas.length;
  const inProgress = ideas.filter((i) =>
    ["submitted", "researching", "validating", "planning", "simulating"].includes(i.status)
  ).length;
  const completed = ideas.filter((i) => i.status === "completed").length;

  return (
    <div className="animate-fade-in">
      {loadError && (
        <div className="glass-card" style={{ marginBottom: 16, padding: 16, border: "1px solid var(--warning)" }}>
          <strong>Data loading issue:</strong> {loadError}
        </div>
      )}

      {/* Stats Grid */}
      <div className={styles.statsGrid}>
        {[
          { label: "Total Ideas", value: String(totalIdeas), icon: "💡", accent: "var(--accent-primary)" },
          { label: "In Progress", value: String(inProgress), icon: "⚙️", accent: "var(--warning)" },
          { label: "Completed", value: String(completed), icon: "✅", accent: "var(--success)" },
          { label: "Credits Left", value: credits !== null ? String(credits) : "—", icon: "💰", accent: "var(--accent-secondary)" },
        ].map((stat) => (
          <div key={stat.label} className={`${styles.statCard} glass-card`}>
            <div className={styles.statIcon}>{stat.icon}</div>
            <div>
              <div className={styles.statValue} style={{ color: stat.accent }}>{stat.value}</div>
              <div className={styles.statLabel}>{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Backend Status */}
      {Object.keys(backendStatus).length > 0 && (
        <div className={`${styles.statusBar} glass-card`}>
          <span className={styles.statusTitle}>🔌 Backend Connected</span>
          <div className={styles.statusServices}>
            {Object.entries(backendStatus).map(([svc, ok]) => (
              <span key={svc} className={`badge ${ok ? "badge-success" : "badge-error"}`}>
                {svc}: {ok ? "✅" : "❌"}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className={styles.quickActions}>
        <h2 className={styles.sectionTitle}>Quick Actions</h2>
        <div className={styles.actionGrid}>
          <Link href="/dashboard/ideas/new" className={`${styles.actionCard} glass-card`} id="action-new-idea">
            <span className={styles.actionIcon}>✨</span>
            <span className={styles.actionLabel}>Submit New Idea</span>
          </Link>
          <Link href="/dashboard/agents" className={`${styles.actionCard} glass-card`} id="action-agents">
            <span className={styles.actionIcon}>🤖</span>
            <span className={styles.actionLabel}>Monitor Agents</span>
          </Link>
          <Link href="/dashboard/workflows" className={`${styles.actionCard} glass-card`} id="action-workflows">
            <span className={styles.actionIcon}>🔄</span>
            <span className={styles.actionLabel}>View Workflow</span>
          </Link>
          <Link href="/dashboard/simulation" className={`${styles.actionCard} glass-card`} id="action-simulate">
            <span className={styles.actionIcon}>🎯</span>
            <span className={styles.actionLabel}>Pitch Simulation</span>
          </Link>
        </div>
      </div>

      {/* Recent Ideas */}
      <div className={styles.recentSection}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Recent Ideas</h2>
          <Link href="/dashboard/ideas" className="btn btn-ghost btn-sm">View All ➔</Link>
        </div>
        <div className={`${styles.ideaList} stagger-children`}>
          {loading ? (
            <>
              <div className={`${styles.ideaCard} glass-card`}><div className="skeleton" style={{ height: 20, width: "60%" }} /><div className="skeleton" style={{ height: 14, width: "30%", marginTop: 8 }} /></div>
              <div className={`${styles.ideaCard} glass-card`}><div className="skeleton" style={{ height: 20, width: "50%" }} /><div className="skeleton" style={{ height: 14, width: "25%", marginTop: 8 }} /></div>
            </>
          ) : ideas.length > 0 ? (
            ideas.slice(0, 5).map((idea) => (
              <Link key={idea.id} href={`/dashboard/ideas/${idea.id}`} className={`${styles.ideaCard} glass-card`}>
                <div className={styles.ideaInfo}>
                  <div className={styles.ideaTitle}>{idea.title}</div>
                  <div className={styles.ideaMeta}>
                    {idea.industry && <span className="badge badge-accent">{idea.industry}</span>}
                    <span className={`badge ${getStatusBadge(idea.status)}`}>{idea.status}</span>
                  </div>
                </div>
                <div className={styles.ideaProgress}>
                  <div className={styles.progressLabel}>{idea.progress}%</div>
                  <div className="progress-bar" style={{ width: "120px" }}>
                    <div className="progress-bar-fill" style={{ width: `${idea.progress}%` }} />
                  </div>
                </div>
              </Link>
            ))
          ) : (
            <div className={`${styles.emptyState} glass-card`}>
              <p>No ideas yet. Submit your first startup idea to get started!</p>
              <Link href="/dashboard/ideas/new" className="btn btn-primary btn-sm">✨ Submit New Idea</Link>
            </div>
          )}
        </div>
      </div>

      {/* Agent Roles */}
      <div className={styles.activitySection}>
        <h2 className={styles.sectionTitle}>Available AI Agents</h2>
        <div className={`${styles.activityFeed} glass-card`}>
          {[
            { agent: "🕵️ Market Analyst", action: "TAM/SAM/SOM, competitor analysis, trend research", status: "ready" },
            { agent: "🏗️ Tech Architect", action: "System design, stack selection, MVP specs", status: "ready" },
            { agent: "📈 Growth Strategist", action: "GTM strategy, pricing, acquisition channels", status: "ready" },
            { agent: "💰 Financial Analyst", action: "Revenue projections, unit economics, funding", status: "ready" },
            { agent: "⚖️ Legal Advisor", action: "IP landscape, compliance, corporate structure", status: "ready" },
          ].map((activity, i) => (
            <div key={i} className={styles.activityItem}>
              <div className={styles.activityAgent}>{activity.agent}</div>
              <div className={styles.activityAction}>{activity.action}</div>
              <div className={styles.activityMeta}>
                <span className="badge badge-success">{activity.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function getStatusBadge(status: string): string {
  const map: Record<string, string> = {
    completed: "badge-success",
    running: "badge-info",
    researching: "badge-info",
    waiting: "badge-warning",
    failed: "badge-error",
    draft: "badge-accent",
    submitted: "badge-info",
  };
  return map[status] || "badge-accent";
}
