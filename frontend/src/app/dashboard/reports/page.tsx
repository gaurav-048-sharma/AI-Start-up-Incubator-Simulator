"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
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

  // Helper to parse basic markdown to HTML for a clean view
  const renderMarkdown = (text: string) => {
    let html = text
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/^\- (.*$)/gim, '<ul><li>$1</li></ul>')
      .replace(/<\/ul>\n<ul>/gim, '')
      .replace(/\n\n/gim, '<p></p>')
      .replace(/\n/gim, '<br />');
    return { __html: html };
  };

  const handleDownloadPDF = () => {
    if (!selectedReport) return;
    const content = String(selectedReport.content?.raw || "");

    // Open a new window and print it to generate a clean PDF
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <html>
          <head>
            <title>${selectedReport.title}</title>
            <style>
              body { font-family: 'Inter', system-ui, sans-serif; line-height: 1.6; color: #111; max-width: 800px; margin: 40px auto; padding: 20px; }
              h1 { color: #222; border-bottom: 2px solid #eaeaea; padding-bottom: 10px; }
              h2 { color: #444; margin-top: 30px; }
              p { margin-bottom: 15px; }
              ul { margin-bottom: 15px; }
              li { margin-bottom: 5px; }
            </style>
          </head>
          <body>
            ${renderMarkdown(content).__html}
            <script>
              window.onload = () => {
                window.print();
                setTimeout(() => window.close(), 500);
              };
            </script>
          </body>
        </html>
      `);
      printWindow.document.close();
    }
  };

  const handleDownloadFullIdeaPDF = (group: { idea: Idea, reports: Report[] }) => {
    // Concatenate all reports into one master document
    let masterMarkdown = `# Master Incubation Portfolio: ${group.idea.title}\n\n`;
    masterMarkdown += `**Industry:** ${group.idea.industry} | **Description:** ${group.idea.description}\n\n---\n\n`;
    
    // Sort reports logically if needed, but we'll just iterate
    group.reports.forEach(report => {
      masterMarkdown += `\n\n<div style="page-break-before: always;"></div>\n\n`;
      masterMarkdown += `<h1>${report.title}</h1>\n\n`;
      masterMarkdown += report.content?.raw || "No content generated.";
    });

    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <html>
          <head>
            <title>${group.idea.title} - Full Master Report</title>
            <style>
              body { font-family: 'Inter', system-ui, sans-serif; line-height: 1.6; color: #111; max-width: 800px; margin: 40px auto; padding: 20px; }
              h1 { color: #222; border-bottom: 2px solid #eaeaea; padding-bottom: 10px; margin-top: 40px; }
              h2 { color: #444; margin-top: 30px; }
              p { margin-bottom: 15px; }
              ul { margin-bottom: 15px; }
              li { margin-bottom: 5px; }
              @media print {
                div[style*="page-break-before"] { page-break-before: always; }
              }
            </style>
          </head>
          <body>
            ${renderMarkdown(masterMarkdown).__html}
            <script>
              window.onload = () => {
                window.print();
                setTimeout(() => window.close(), 500);
              };
            </script>
          </body>
        </html>
      `);
      printWindow.document.close();
    }
  };

  // Group reports by Idea
  const groupedReports = ideas.map(idea => ({
    idea,
    reports: reports.filter(r => r.idea_id === idea.id)
  })).filter(g => g.reports.length > 0);

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
      ) : groupedReports.length > 0 ? (
        <div className="stagger-children">
          {groupedReports.map((group) => (
            <div key={group.idea.id} className={styles.ideaSection}>
              <div className={styles.ideaHeader}>
                <h3>💡 {group.idea.title}</h3>
                <span className="badge badge-accent">{group.idea.industry}</span>
                <button 
                  className="btn btn-primary btn-sm" 
                  onClick={() => handleDownloadFullIdeaPDF(group)} 
                  style={{ marginLeft: "auto" }}
                >
                  Download Master PDF
                </button>
              </div>
              <div className={styles.ideaReports}>
                {group.reports.map((report) => (
                  <div key={report.id} className={styles.reportCard}>
                    <div className={styles.reportIcon}>{REPORT_ICONS[report.report_type] || "📄"}</div>
                    <div className={styles.reportInfo}>
                      <div className={styles.reportTitle}>{report.title}</div>
                      <div className={styles.reportMeta}>
                        <span className={styles.reportDate}>{new Date(report.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className={styles.reportActions}>
                      <button className="btn btn-primary btn-sm" onClick={() => setSelectedReport(report)}>View Report</button>
                    </div>
                  </div>
                ))}
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
      {selectedReport && typeof document !== "undefined" && createPortal(
        <div className={styles.modal} onClick={() => setSelectedReport(null)}>
          <div className={`${styles.modalContent} glass-card`} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>{selectedReport.title}</h2>
              <div style={{ display: "flex", gap: "10px" }}>
                <button className="btn btn-primary btn-sm" onClick={handleDownloadPDF}>Download PDF</button>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelectedReport(null)}>✕</button>
              </div>
            </div>
            <div className={styles.modalBody}>
              <div
                className={styles.markdownContainer}
                dangerouslySetInnerHTML={renderMarkdown(String(selectedReport.content?.raw || "No content generated yet."))}
              />
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
