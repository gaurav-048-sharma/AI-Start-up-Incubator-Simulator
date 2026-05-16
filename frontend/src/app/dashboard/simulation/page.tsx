"use client";

import { useState, useEffect } from "react";
import styles from "./simulation.module.css";
import { ideasApi, simulationsApi, type Idea, type Simulation } from "@/lib/api";

const INVESTORS = [
  { name: "Sarah Chen", firm: "Horizon Ventures", role: "VC Partner", style: "Analytical", avatar: "👩‍💼" },
  { name: "Marcus Johnson", firm: "Independent", role: "Angel Investor", style: "Visionary", avatar: "👨‍💻" },
  { name: "Dr. Priya Patel", firm: "TechCorp Ventures", role: "Strategic CVC", style: "Technical", avatar: "👩‍🔬" },
];

export default function SimulationPage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [selectedIdea, setSelectedIdea] = useState<string>("");
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await ideasApi.list();
        const ideaList = data.ideas || [];
        setIdeas(ideaList);
        if (ideaList.length > 0) setSelectedIdea(ideaList[0].id);
      } catch { /* empty */ }
      finally { setLoading(false); }
    }
    load();
  }, []);

  const handleStartPitch = async () => {
    if (!selectedIdea) return;
    setIsRunning(true);
    setError("");
    try {
      const result = await simulationsApi.start(selectedIdea);
      setSimulation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed — ensure the idea has completed the incubation workflow first.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <p className={styles.subtitle}>Pitch your startup to AI investor agents and receive real-time feedback.</p>

      {/* Investor Panel */}
      <div className={styles.investorPanel}>
        <h3 className={styles.panelTitle}>Investor Panel</h3>
        <div className={styles.investorGrid}>
          {INVESTORS.map((inv) => (
            <div key={inv.name} className={`${styles.investorCard} glass-card`}>
              <div className={styles.investorAvatar}>{inv.avatar}</div>
              <div className={styles.investorName}>{inv.name}</div>
              <div className={styles.investorFirm}>{inv.firm}</div>
              <div className={styles.investorMeta}>
                <span className="badge badge-accent">{inv.role}</span>
                <span className="badge badge-info">{inv.style}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className={`${styles.controls} glass-card`}>
        <div className={styles.controlRow}>
          <div style={{ flex: 1 }}>
            <label className="input-label">Select Idea to Pitch</label>
            <select className="input" value={selectedIdea} onChange={(e) => setSelectedIdea(e.target.value)} disabled={loading || isRunning}>
              {ideas.length === 0 && <option value="">No ideas available</option>}
              {ideas.map((idea) => (
                <option key={idea.id} value={idea.id}>{idea.title} ({idea.status})</option>
              ))}
            </select>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleStartPitch}
            disabled={!selectedIdea || isRunning}
            id="start-pitch-btn"
          >
            {isRunning ? (<><span className="loader" /> Running Pitch...</>) : "🎯 Start Pitch Simulation"}
          </button>
        </div>
        {error && (
          <div style={{ padding: "var(--space-3)", background: "var(--error-soft)", border: "1px solid var(--error)", borderRadius: "var(--radius-md)", color: "var(--error)", fontSize: "var(--fs-sm)", marginTop: "var(--space-3)" }}>
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {simulation && (
        <div className={`${styles.chatContainer} glass-card`} style={{ marginTop: "var(--space-6)" }}>
          <div className={styles.chatHeader}>
            <h3>Pitch Results</h3>
            {simulation.outcome && <span className={`badge badge-${simulation.outcome === "funded" ? "success" : "warning"}`}>{simulation.outcome}</span>}
          </div>

          {simulation.funding_offered && (
            <div style={{ padding: "var(--space-4) var(--space-5)", borderBottom: "1px solid var(--border-subtle)", display: "flex", gap: "var(--space-6)" }}>
              <div><span style={{ color: "var(--text-muted)", fontSize: "var(--fs-xs)" }}>Funding Offered</span><div style={{ fontSize: "var(--fs-lg)", fontWeight: 700, color: "var(--success)" }}>${(simulation.funding_offered / 1e6).toFixed(1)}M</div></div>
              {simulation.valuation && <div><span style={{ color: "var(--text-muted)", fontSize: "var(--fs-xs)" }}>Valuation</span><div style={{ fontSize: "var(--fs-lg)", fontWeight: 700, color: "var(--accent-tertiary)" }}>${(simulation.valuation / 1e6).toFixed(1)}M</div></div>}
            </div>
          )}

          <div className={styles.chatMessages}>
            {simulation.transcript.map((msg, i) => (
              <div key={i} className={`${styles.message} ${msg.role === "founder" ? styles.messageFounder : styles.messageInvestor}`}>
                <div className={styles.messageSpeaker}>
                  {msg.role === "founder" ? "🚀" : "💼"} {msg.speaker}
                </div>
                <div className={styles.messageContent}>{msg.content}</div>
              </div>
            ))}
            {simulation.transcript.length === 0 && (
              <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "var(--space-8)" }}>
                Simulation completed but no transcript was generated.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
