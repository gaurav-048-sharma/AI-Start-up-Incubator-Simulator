"use client";

import Link from "next/link";
import styles from "./detail.module.css";

const PHASES = [
  { id: "research", label: "Research", icon: "🔍", status: "completed" },
  { id: "validate", label: "Validate", icon: "✅", status: "completed" },
  { id: "plan", label: "Plan", icon: "📋", status: "active" },
  { id: "build", label: "Build", icon: "🏗️", status: "pending" },
  { id: "simulate", label: "Simulate", icon: "🎯", status: "pending" },
];

export default function IdeaDetailPage() {
  return (
    <div className="animate-fade-in">
      <div className={styles.header}>
        <div>
          <Link href="/dashboard/ideas" className={styles.backLink}>← Back to Ideas</Link>
          <h1 className={styles.title}>AI Resume Builder</h1>
          <div className={styles.meta}>
            <span className="badge badge-info">researching</span>
            <span className="badge badge-accent">HR Tech</span>
            <span className={styles.date}>Created May 15, 2025</span>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button className="btn btn-secondary btn-sm">✏️ Edit</button>
          <button className="btn btn-primary btn-sm">🚀 Relaunch</button>
        </div>
      </div>

      {/* Progress Timeline */}
      <div className={`${styles.timeline} glass-card`}>
        <h3 className={styles.timelineTitle}>Incubation Progress</h3>
        <div className={styles.phases}>
          {PHASES.map((phase, i) => (
            <div key={phase.id} className={`${styles.phase} ${styles[`phase_${phase.status}`]}`}>
              <div className={styles.phaseIcon}>{phase.icon}</div>
              <div className={styles.phaseLabel}>{phase.label}</div>
              {i < PHASES.length - 1 && <div className={styles.phaseConnector} />}
            </div>
          ))}
        </div>
        <div className="progress-bar" style={{ marginTop: "var(--space-4)" }}>
          <div className="progress-bar-fill" style={{ width: "45%" }} />
        </div>
      </div>

      {/* Content Grid */}
      <div className={styles.contentGrid}>
        <div className={`${styles.descCard} glass-card`}>
          <h3>Description</h3>
          <p>An AI-powered resume builder that creates tailored resumes for each job application, analyzing job descriptions and matching candidate skills automatically.</p>
          <h4>Problem Statement</h4>
          <p>Job seekers spend hours customizing resumes for each application. Generic resumes have low success rates, but personalization is time-consuming.</p>
          <h4>Proposed Solution</h4>
          <p>AI analyzes job descriptions and candidate profiles to generate perfectly tailored resumes in seconds, with ATS optimization built in.</p>
        </div>

        <div className={`${styles.agentsCard} glass-card`}>
          <h3>Agent Status</h3>
          <div className={styles.agentList}>
            {[
              { name: "Market Analyst", status: "completed", icon: "🔬" },
              { name: "Tech Architect", status: "running", icon: "🏗️" },
              { name: "Growth Strategist", status: "waiting", icon: "🚀" },
              { name: "Financial Analyst", status: "waiting", icon: "💹" },
              { name: "Legal Advisor", status: "waiting", icon: "⚖️" },
            ].map((a) => (
              <div key={a.name} className={styles.agentRow}>
                <span>{a.icon} {a.name}</span>
                <span className={`badge badge-${a.status === "completed" ? "success" : a.status === "running" ? "info" : "warning"}`}>
                  {a.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
