"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { ideasApi, type IdeaUpdate } from "@/lib/api";

export default function EditIdeaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [form, setForm] = useState<IdeaUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const idea = await ideasApi.get(id);
        setForm({
          title: idea.title,
          description: idea.description,
          industry: idea.industry || "",
          target_market: idea.target_market || "",
          problem_statement: idea.problem_statement || "",
          proposed_solution: idea.proposed_solution || "",
        });
      } catch (err) {
        setError("Failed to load idea");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const updateField = (field: keyof IdeaUpdate, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      await ideasApi.update(id, form);
      router.push(`/dashboard/ideas/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update idea");
      setSaving(false);
    }
  };

  if (loading) return <div className="animate-fade-in"><div className="skeleton" style={{ height: 200, width: "100%" }} /></div>;
  if (error && !form.title) return <div className="animate-fade-in"><h2>⚠️ {error}</h2></div>;

  return (
    <div className="animate-fade-in" style={{ maxWidth: 800, margin: "0 auto" }}>
      <h1 style={{ marginBottom: "var(--space-6)" }}>Edit Idea</h1>
      
      <div className="glass-card" style={{ padding: "var(--space-6)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        <div>
          <label className="input-label" htmlFor="title">Startup Name / Title *</label>
          <input id="title" className="input" value={form.title || ""} onChange={(e) => updateField("title", e.target.value)} />
        </div>
        
        <div>
          <label className="input-label" htmlFor="description">Description *</label>
          <textarea id="description" className="input textarea" value={form.description || ""} onChange={(e) => updateField("description", e.target.value)} />
        </div>
        
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
          <div>
            <label className="input-label" htmlFor="industry">Industry</label>
            <input id="industry" className="input" value={form.industry || ""} onChange={(e) => updateField("industry", e.target.value)} />
          </div>
          <div>
            <label className="input-label" htmlFor="target_market">Target Market</label>
            <input id="target_market" className="input" value={form.target_market || ""} onChange={(e) => updateField("target_market", e.target.value)} />
          </div>
        </div>
        
        <div>
          <label className="input-label" htmlFor="problem">Problem Statement</label>
          <textarea id="problem" className="input textarea" value={form.problem_statement || ""} onChange={(e) => updateField("problem_statement", e.target.value)} />
        </div>
        
        <div>
          <label className="input-label" htmlFor="solution">Proposed Solution</label>
          <textarea id="solution" className="input textarea" value={form.proposed_solution || ""} onChange={(e) => updateField("proposed_solution", e.target.value)} />
        </div>
        
        {error && <div style={{ color: "var(--error)", fontSize: "var(--fs-sm)" }}>{error}</div>}
        
        <div style={{ display: "flex", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
          <button className="btn btn-secondary" onClick={() => router.push(`/dashboard/ideas/${id}`)} disabled={saving}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving || !form.title || !form.description}>
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
