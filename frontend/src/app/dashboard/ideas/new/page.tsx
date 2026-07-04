"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./new.module.css";
import { ideasApi } from "@/lib/api";

export default function NewIdeaPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    title: "", description: "", industry: "", target_market: "",
    problem_statement: "", proposed_solution: "",
  });
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  const updateField = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    setProgress(0);

    // Simulate progress while backend works
    const interval = setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + Math.floor(Math.random() * 15) + 5 : prev));
    }, 400);

    try {
      // Create the idea via backend API
      const idea = await ideasApi.create(form);
      setProgress(50);

      // Launch the incubation workflow
      await ideasApi.launch(idea.id);

      setProgress(100);
      clearInterval(interval);

      // Brief delay so the user sees 100% completion before navigating
      setTimeout(() => {
        router.push(`/dashboard/ideas/${idea.id}`);
      }, 500);
    } catch (err) {
      clearInterval(interval);
      setError(err instanceof Error ? err.message : "Failed to create idea. Is the backend running?");
      setLoading(false);
      setProgress(0);
    }
  };

  return (
    <div className={`${styles.wrapper} animate-fade-in`}>
      {/* Progress Steps */}
      <div className={styles.steps}>
        {["Basics", "Problem & Solution", "Review & Launch"].map((label, i) => (
          <div key={label} className={`${styles.step} ${step >= i + 1 ? styles.stepActive : ""}`}>
            <div className={styles.stepCircle}>{i + 1}</div>
            <span className={styles.stepLabel}>{label}</span>
          </div>
        ))}
      </div>

      <div className={`${styles.formCard} glass-card`}>
        {/* Step 1: Basics */}
        {step === 1 && (
          <div className={styles.stepContent}>
            <h2 className={styles.stepTitle}>Tell us about your idea</h2>
            <p className={styles.stepDesc}>Start with the basics — our AI agents will do the deep research.</p>
            
            <button 
              className="btn btn-secondary" 
              style={{ marginBottom: '1rem', fontSize: '0.9rem', padding: '0.5rem 1rem' }}
              onClick={() => {
                setForm({
                  title: "EcoTrack — AI Carbon Footprint Tracker",
                  description: "EcoTrack is an AI-powered SaaS that helps mid-sized businesses measure, track, and reduce their carbon footprint in real-time.",
                  industry: "CleanTech",
                  target_market: "SMBs",
                  problem_statement: "Climate change is accelerating, but 78% of businesses cannot accurately measure their carbon emissions due to fragmented data and complex supply chains.",
                  proposed_solution: "EcoTrack uses AI to automate carbon footprint calculation by connecting to 200+ ERP and accounting systems, providing actionable insights for reduction."
                });
              }}
            >
              🧪 Fill with Dummy Data
            </button>

            <div className={styles.fieldGroup}>
              <label className="input-label" htmlFor="title">Startup Name / Title *</label>
              <input id="title" className="input" placeholder="e.g., AI Resume Builder" value={form.title}
                onChange={(e) => updateField("title", e.target.value)} />
            </div>
            <div className={styles.fieldGroup}>
              <label className="input-label" htmlFor="description">Description *</label>
              <textarea id="description" className="input textarea"
                placeholder="Describe your startup idea in detail — what it does, who it's for, and why it matters."
                value={form.description} onChange={(e) => updateField("description", e.target.value)} />
            </div>
            <div className={styles.fieldRow}>
              <div className={styles.fieldGroup}>
                <label className="input-label" htmlFor="industry">Industry</label>
                <input id="industry" className="input" placeholder="e.g., FinTech, HealthTech" value={form.industry}
                  onChange={(e) => updateField("industry", e.target.value)} />
              </div>
              <div className={styles.fieldGroup}>
                <label className="input-label" htmlFor="target_market">Target Market</label>
                <input id="target_market" className="input" placeholder="e.g., SMBs, Enterprise, Consumers"
                  value={form.target_market} onChange={(e) => updateField("target_market", e.target.value)} />
              </div>
            </div>
            <div className={styles.actions}>
              <button className="btn btn-primary" onClick={() => setStep(2)}
                disabled={form.title.length < 3 || form.description.length < 20}>Next: Problem & Solution →</button>
              {(form.title.length > 0 && form.title.length < 3) && <div className={styles.errorMsg} style={{fontSize: '0.8rem', marginTop:'8px'}}>Title must be at least 3 characters.</div>}
              {(form.description.length > 0 && form.description.length < 20) && <div className={styles.errorMsg} style={{fontSize: '0.8rem', marginTop:'4px'}}>Description must be at least 20 characters.</div>}
            </div>
          </div>
        )}

        {/* Step 2: Problem & Solution */}
        {step === 2 && (
          <div className={styles.stepContent}>
            <h2 className={styles.stepTitle}>Problem & Solution</h2>
            <p className={styles.stepDesc}>Help our agents understand the core problem and your approach.</p>
            <div className={styles.fieldGroup}>
              <label className="input-label" htmlFor="problem">Problem Statement</label>
              <textarea id="problem" className="input textarea"
                placeholder="What specific problem does this solve? Who experiences this pain?"
                value={form.problem_statement} onChange={(e) => updateField("problem_statement", e.target.value)} />
            </div>
            <div className={styles.fieldGroup}>
              <label className="input-label" htmlFor="solution">Proposed Solution</label>
              <textarea id="solution" className="input textarea"
                placeholder="How does your product solve this problem? What's unique about your approach?"
                value={form.proposed_solution} onChange={(e) => updateField("proposed_solution", e.target.value)} />
            </div>
            <div className={styles.actions}>
              <button className="btn btn-secondary" onClick={() => setStep(1)}>← Back</button>
              <button className="btn btn-primary" onClick={() => setStep(3)}>Review & Launch →</button>
            </div>
          </div>
        )}

        {/* Step 3: Review & Launch */}
        {step === 3 && (
          <div className={styles.stepContent}>
            <h2 className={styles.stepTitle}>Review & Launch</h2>
            <p className={styles.stepDesc}>Review your idea before launching the AI incubation workflow.</p>
            <div className={`${styles.reviewCard} glass-card`}>
              <div className={styles.reviewItem}><strong>Title:</strong> {form.title}</div>
              <div className={styles.reviewItem}><strong>Description:</strong> {form.description}</div>
              {form.industry && <div className={styles.reviewItem}><strong>Industry:</strong> {form.industry}</div>}
              {form.target_market && <div className={styles.reviewItem}><strong>Target Market:</strong> {form.target_market}</div>}
              {form.problem_statement && <div className={styles.reviewItem}><strong>Problem:</strong> {form.problem_statement}</div>}
              {form.proposed_solution && <div className={styles.reviewItem}><strong>Solution:</strong> {form.proposed_solution}</div>}
            </div>
            <div className={styles.launchInfo}>
              <h3>🚀 What happens next?</h3>
              <ol>
                <li>Market Analyst researches your market, competitors, and opportunity</li>
                <li>Tech Architect designs the technical blueprint</li>
                <li>Growth Strategist creates your go-to-market plan</li>
                <li>Financial Analyst builds revenue projections</li>
                <li>Legal Advisor reviews IP and compliance</li>
                <li>You pitch to AI investor agents</li>
              </ol>
            </div>
            <div className={styles.actions}>
              {!loading && (
                <>
                  <button className="btn btn-secondary" onClick={() => setStep(2)}>← Back</button>
                  {error && <div className={styles.errorMsg}>{error}</div>}
                  <button className="btn btn-primary btn-lg" onClick={handleSubmit} id="launch-btn">
                    🚀 Launch Incubation
                  </button>
                </>
              )}
            </div>
            {loading && (
              <div className={styles.progressWrapper}>
                <div className={styles.progressContainer}>
                  <div className={styles.progressBar} style={{ width: `${Math.min(progress, 100)}%` }} />
                </div>
                <span className={styles.progressText}>
                  {progress < 100 ? `Initializing AI Agents... ${progress}%` : "Redirecting to Dashboard..."}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
