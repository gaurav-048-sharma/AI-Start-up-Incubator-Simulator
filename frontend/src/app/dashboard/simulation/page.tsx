"use client";

import { useState, useEffect, useRef } from "react";
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
  const [isSending, setIsSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [messageInput, setMessageInput] = useState("");
  const [pastSimulations, setPastSimulations] = useState<Simulation[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadSims() {
      if (!selectedIdea) {
        setPastSimulations([]);
        return;
      }
      try {
        const res = await simulationsApi.listForIdea(selectedIdea);
        setPastSimulations(res.simulations || []);
      } catch {
        setPastSimulations([]);
      }
    }
    loadSims();
  }, [selectedIdea, simulation]);

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

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [simulation?.transcript]);

  const handleStartPitch = async () => {
    if (!selectedIdea) return;
    setIsRunning(true);
    setError("");
    setSimulation(null);
    try {
      const result = await simulationsApi.start(selectedIdea);
      setSimulation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed — ensure the idea has completed the incubation workflow first.");
    } finally {
      setIsRunning(false);
    }
  };

  const handleSendMessage = async () => {
    if (!messageInput.trim() || !simulation || isSending) return;
    
    setIsSending(true);
    const content = messageInput;
    setMessageInput("");
    
    // Optimistic update
    setSimulation(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        transcript: [
          ...prev.transcript,
          { speaker: "Founder", role: "founder", content, timestamp: new Date().toISOString() }
        ]
      };
    });

    try {
      const result = await simulationsApi.sendMessage(simulation.id, content);
      setSimulation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message.");
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleDeleteSimulation = async (simId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this session?")) return;
    try {
      await simulationsApi.delete(simId);
      setPastSimulations(prev => prev.filter(s => s.id !== simId));
      if (simulation?.id === simId) {
        setSimulation(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete simulation");
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 80px)", overflow: "hidden" }}>
      <p className={styles.subtitle} style={{ flexShrink: 0 }}>Pitch your startup to AI investor agents and receive real-time feedback.</p>

      {/* Investor Panel */}
      <div className={styles.investorPanel} style={{ flexShrink: 0, marginBottom: "var(--space-4)" }}>
        <h3 className={styles.panelTitle}>Investor Panel</h3>
        <div className={styles.investorGrid} style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          {INVESTORS.map((inv) => (
            <div key={inv.name} className={`${styles.investorCard} glass-card`} style={{ padding: "var(--space-3)" }}>
              <div className={styles.investorAvatar} style={{ fontSize: "2rem" }}>{inv.avatar}</div>
              <div className={styles.investorName} style={{ fontSize: "var(--fs-sm)" }}>{inv.name}</div>
              <div className={styles.investorFirm} style={{ fontSize: "var(--fs-xs)" }}>{inv.firm}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, gap: "var(--space-4)", overflow: "hidden" }}>
        {/* History Sidebar */}
        <div className="glass-card" style={{ width: "250px", display: "flex", flexDirection: "column", flexShrink: 0, padding: "var(--space-4)" }}>
          <h4 style={{ margin: "0 0 var(--space-3) 0", fontSize: "var(--fs-sm)", textTransform: "uppercase", letterSpacing: "1px", color: "var(--text-muted)" }}>History</h4>
          <div style={{ overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            {pastSimulations.length === 0 && <div style={{ fontSize: "var(--fs-sm)", color: "var(--text-muted)" }}>No previous sessions</div>}
            {pastSimulations.map(sim => (
              <div key={sim.id} 
                   onClick={() => setSimulation(sim)}
                   style={{ padding: "var(--space-3)", background: simulation?.id === sim.id ? "var(--primary-subtle)" : "var(--bg-elevated)", border: `1px solid ${simulation?.id === sim.id ? "var(--primary)" : "var(--border-subtle)"}`, borderRadius: "var(--radius-md)", cursor: "pointer", transition: "all 0.2s ease" }}>
                <div style={{ fontSize: "var(--fs-sm)", fontWeight: 600, color: "var(--text-primary)", marginBottom: "var(--space-1)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>{new Date(sim.started_at).toLocaleDateString()} {new Date(sim.started_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                  <button onClick={(e) => handleDeleteSimulation(sim.id, e)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--error)", padding: "var(--space-1)" }} title="Delete Session">🗑️</button>
                </div>
                <div style={{ fontSize: "var(--fs-xs)", color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
                  <span>{sim.transcript.filter(m => m.role === 'founder').length} Rounds</span>
                  <span style={{ color: sim.status === "active" ? "var(--accent)" : "var(--text-muted)" }}>{sim.status === "active" ? "Active" : "Completed"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Main Content Area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {!simulation && (
        <div className={`${styles.controls} glass-card`} style={{ flexShrink: 0 }}>
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
              {isRunning ? (<><span className="loader" /> Preparing Pitch...</>) : "🎯 Start Pitch Simulation"}
            </button>
          </div>
          {error && (
            <div style={{ padding: "var(--space-3)", background: "var(--error-soft)", border: "1px solid var(--error)", borderRadius: "var(--radius-md)", color: "var(--error)", fontSize: "var(--fs-sm)", marginTop: "var(--space-3)" }}>
              {error}
            </div>
          )}
        </div>
      )}

      {/* Active Simulation Chat Area */}
      {simulation && (
        <div className="glass-card" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          
          <div style={{ padding: "var(--space-4)", borderBottom: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h3 style={{ margin: 0 }}>Simulation Session</h3>
              <div style={{ fontSize: "var(--fs-xs)", color: "var(--text-muted)" }}>
                {ideas.find(i => i.id === simulation.idea_id)?.title}
              </div>
            </div>
            <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
              {simulation.status === "active" ? (
                <span className="badge badge-accent">Active Pitch</span>
              ) : (
                <span className={`badge badge-${simulation.outcome === "funded" ? "success" : "warning"}`}>{simulation.outcome?.toUpperCase() || "COMPLETED"}</span>
              )}
              <button 
                className="btn btn-secondary" 
                onClick={() => setSimulation(null)}
                style={{ padding: "var(--space-1) var(--space-3)", fontSize: "var(--fs-xs)" }}
              >
                Close
              </button>
            </div>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            {simulation.transcript.map((msg, i) => (
              <div key={i} className={`${styles.message} ${msg.role === "founder" ? styles.messageFounder : styles.messageInvestor}`} style={{ maxWidth: "80%", alignSelf: msg.role === "founder" ? "flex-end" : "flex-start", padding: "var(--space-3) var(--space-4)", borderRadius: "var(--radius-lg)", background: msg.role === "founder" ? "var(--primary-subtle)" : "var(--bg-elevated)", border: `1px solid ${msg.role === "founder" ? "var(--primary)" : "var(--border-subtle)"}` }}>
                <div style={{ fontSize: "var(--fs-xs)", color: "var(--text-muted)", marginBottom: "var(--space-1)", fontWeight: 600 }}>
                  {msg.role === "founder" ? "🚀 You" : `💼 ${msg.speaker}`}
                </div>
                <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{msg.content}</div>
              </div>
            ))}
            {isSending && (
              <div style={{ alignSelf: "flex-start", padding: "var(--space-3) var(--space-4)", borderRadius: "var(--radius-lg)", background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)", color: "var(--text-muted)", fontSize: "var(--fs-sm)" }}>
                <span className="loader" style={{ marginRight: "var(--space-2)" }}/> 
                Investors are deliberating...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {error && (
            <div style={{ margin: "var(--space-3)", padding: "var(--space-3)", background: "var(--error-soft)", border: "1px solid var(--error)", borderRadius: "var(--radius-md)", color: "var(--error)", fontSize: "var(--fs-sm)" }}>
              {error}
            </div>
          )}

          {simulation.status === "completed" && (
            <div style={{ padding: "var(--space-4)", borderTop: "1px solid var(--border-subtle)", background: "var(--bg-elevated)" }}>
              <h4 style={{ marginBottom: "var(--space-3)", color: simulation.outcome === "funded" ? "var(--success)" : "var(--text-primary)" }}>Final Verdict</h4>
              
              {simulation.funding_offered && (
                <div style={{ display: "flex", gap: "var(--space-6)", marginBottom: "var(--space-4)" }}>
                  <div><span style={{ color: "var(--text-muted)", fontSize: "var(--fs-xs)" }}>Funding Offered</span><div style={{ fontSize: "var(--fs-lg)", fontWeight: 700, color: "var(--success)" }}>${(simulation.funding_offered / 1e6).toFixed(1)}M</div></div>
                  {simulation.valuation && <div><span style={{ color: "var(--text-muted)", fontSize: "var(--fs-xs)" }}>Valuation</span><div style={{ fontSize: "var(--fs-lg)", fontWeight: 700, color: "var(--accent-tertiary)" }}>${(simulation.valuation / 1e6).toFixed(1)}M</div></div>}
                </div>
              )}
              
              <button className="btn btn-secondary" onClick={() => setSimulation(null)} style={{ width: "100%" }}>Pitch Another Idea</button>
            </div>
          )}

          {simulation.status === "active" && (
            <div style={{ padding: "var(--space-4)", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "var(--space-3)" }}>
              <textarea 
                className="input" 
                style={{ flex: 1, minHeight: "60px", resize: "none" }} 
                placeholder="Type your response... (Press Enter to send, Shift+Enter for new line)"
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isSending}
              />
              <button 
                className="btn btn-primary" 
                onClick={handleSendMessage}
                disabled={isSending || !messageInput.trim()}
                style={{ alignSelf: "flex-end", height: "60px", padding: "0 var(--space-5)" }}
              >
                Send
              </button>
            </div>
          )}

        </div>
      )}
      </div>
    </div>
    </div>
  );
}
