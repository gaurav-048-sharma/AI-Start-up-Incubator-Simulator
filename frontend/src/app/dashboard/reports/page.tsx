"use client";

import styles from "./reports.module.css";

const REPORTS = [
  { id: "1", type: "market_analysis", title: "Market Research Report", idea: "AI Resume Builder", date: "May 15, 2025", icon: "📊" },
  { id: "2", type: "tech_architecture", title: "Technical Architecture", idea: "AI Resume Builder", date: "May 15, 2025", icon: "⚙️" },
  { id: "3", type: "growth_strategy", title: "Growth Strategy", idea: "AI Resume Builder", date: "May 15, 2025", icon: "📈" },
  { id: "4", type: "financial_projection", title: "Financial Projections", idea: "AI Resume Builder", date: "May 15, 2025", icon: "💰" },
  { id: "5", type: "legal_review", title: "Legal & IP Review", idea: "AI Resume Builder", date: "May 15, 2025", icon: "⚖️" },
  { id: "6", type: "executive_summary", title: "Executive Summary", idea: "AI Resume Builder", date: "May 15, 2025", icon: "📝" },
  { id: "7", type: "pitch_deck", title: "Pitch Deck", idea: "AI Resume Builder", date: "May 15, 2025", icon: "🎯" },
];

export default function ReportsPage() {
  return (
    <div className="animate-fade-in">
      <p className={styles.subtitle}>View and download all AI-generated reports for your startup ideas.</p>

      <div className={`${styles.reportsGrid} stagger-children`}>
        {REPORTS.map((report) => (
          <div key={report.id} className={`${styles.reportCard} glass-card`}>
            <div className={styles.reportIcon}>{report.icon}</div>
            <div className={styles.reportInfo}>
              <div className={styles.reportTitle}>{report.title}</div>
              <div className={styles.reportMeta}>
                <span className="badge badge-accent">{report.idea}</span>
                <span className={styles.reportDate}>{report.date}</span>
              </div>
            </div>
            <div className={styles.reportActions}>
              <button className="btn btn-ghost btn-sm">View</button>
              <button className="btn btn-secondary btn-sm">⬇ Download</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
