"use client";

import { useState, useEffect } from "react";
import styles from "./reports.module.css";
import { reportsApi, ideasApi, type Report, type Idea } from "@/lib/api";

const REPORT_ICONS: Record<string, string> = {
  market_analysis: "📊", tech_architecture: "⚙️", growth_strategy: "📈",
  financial_projection: "💰", legal_review: "⚖️", executive_summary: "📝",
  pitch_deck: "🎯", full_report: "📋",
};

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const ideasData = await ideasApi.list();
        const ideaList = ideasData.ideas || [];
        setIdeas(ideaList);

        // Fetch reports for all ideas
        const allReports: Report[] = [];
        for (const idea of ideaList) {
          try {
            const r = await reportsApi.listForIdea(idea.id);
            if (Array.isArray(r)) allReports.push(...r);
          } catch { /* skip */ }
        }
        setReports(allReports);
      } catch {
        setReports([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const getIdeaTitle = (ideaId: string) => {
    return ideas.find((i) => i.id === ideaId)?.title || "Unknown Idea";
  };

  return (
    <div className="animate-fade-in">
      <p className={styles.subtitle}>View and download all AI-generated reports for your startup ideas.</p>

      {loading ? (
        <div className={styles.reportsGrid}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className={`${styles.reportCard} glass-card`}>
              <div className="skeleton" style={{ width: 32, height: 32, borderRadius: "50%" }} />
              <div style={{ flex: 1 }}>
                <div className="skeleton" style={{ height: 16, width: "60%", marginBottom: 8 }} />
                <div className="skeleton" style={{ height: 12, width: "40%" }} />
              </div>
            </div>
          ))}
        </div>
      ) : reports.length > 0 ? (
        <div className={`${styles.reportsGrid} stagger-children`}>
          {reports.map((report) => (
            <div key={report.id} className={`${styles.reportCard} glass-card`}>
              <div className={styles.reportIcon}>{REPORT_ICONS[report.report_type] || "📄"}</div>
              <div className={styles.reportInfo}>
                <div className={styles.reportTitle}>{report.title}</div>
                <div className={styles.reportMeta}>
                  <span className="badge badge-accent">{getIdeaTitle(report.idea_id)}</span>
                  <span className={styles.reportDate}>{new Date(report.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className={styles.reportActions}>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelectedReport(report)}>View</button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-card" style={{ padding: "var(--space-10)", textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)", fontSize: "var(--fs-sm)" }}>
            No reports generated yet. Submit an idea and launch the incubation workflow to generate reports.
          </p>
        </div>
      )}

      {/* Report Viewer Modal */}
      {selectedReport && (
        <div className={styles.modal} onClick={() => setSelectedReport(null)}>
          <div className={`${styles.modalContent} glass-card`} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>{selectedReport.title}</h2>
              <button className="btn btn-ghost btn-sm" onClick={() => setSelectedReport(null)}>✕</button>
            </div>
            <div className={styles.modalBody}>
              <pre>{JSON.stringify(selectedReport.content, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
