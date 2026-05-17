"use client";

import { useState, useEffect } from "react";
import styles from "./compare.module.css";
import { ideasApi, comparisonApi, type Idea, type ComparisonResult } from "@/lib/api";

export default function ComparePage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await ideasApi.list();
        setIdeas(data.ideas || []);
      } catch { /* empty */ }
      finally { setLoading(false); }
    }
    load();
  }, []);

  const toggleIdea = (id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
    setResult(null);
  };

  const handleCompare = async () => {
    if (selected.length < 2) return;
    setComparing(true);
    setError("");
    try {
      const data = await comparisonApi.compare(selected);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setComparing(false);
    }
  };

  const getMaxScore = (dim: ComparisonResult["dimensions"][0]) => {
    return Math.max(...Object.values(dim.scores), 0.01);
  };

  return (
    <div className="animate-fade-in">
      <p className={styles.subtitle}>
        Select 2–4 ideas to compare across market readiness, research depth, investor appeal, and more.
      </p>

      {/* Idea Selection */}
      <div className={`${styles.selectionPanel} glass-card`}>
        <h3 className={styles.panelTitle}>Select Ideas to Compare</h3>
        {loading ? (
          <div style={{ display: "flex", gap: "var(--space-3)" }}>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton" style={{ height: 60, flex: 1, borderRadius: "var(--radius-md)" }} />
            ))}
          </div>
        ) : ideas.length < 2 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "var(--fs-sm)" }}>
            You need at least 2 ideas to compare. Submit more ideas first.
          </p>
        ) : (
          <div className={styles.ideaChips}>
            {ideas.map((idea) => {
              const isSelected = selected.includes(idea.id);
              return (
                <button
                  key={idea.id}
                  className={`${styles.ideaChip} ${isSelected ? styles.ideaChipSelected : ""}`}
                  onClick={() => toggleIdea(idea.id)}
                  disabled={!isSelected && selected.length >= 4}
                >
                  <span className={styles.chipCheck}>{isSelected ? "✓" : "○"}</span>
                  <div className={styles.chipInfo}>
                    <div className={styles.chipTitle}>{idea.title}</div>
                    <div className={styles.chipMeta}>
                      {idea.industry && <span className="badge badge-accent">{idea.industry}</span>}
                      <span className={`badge badge-${idea.status === "completed" ? "success" : "info"}`}>
                        {idea.status}
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        <div className={styles.selectionFooter}>
          <span className={styles.selectionCount}>{selected.length}/4 selected</span>
          <button
            className="btn btn-primary"
            onClick={handleCompare}
            disabled={selected.length < 2 || comparing}
            id="compare-btn"
          >
            {comparing ? (<><span className="loader" /> Comparing...</>) : "📊 Compare Ideas"}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "var(--space-3)", background: "var(--error-soft)", border: "1px solid var(--error)", borderRadius: "var(--radius-md)", color: "var(--error)", fontSize: "var(--fs-sm)", marginTop: "var(--space-4)" }}>
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className={styles.resultsSection}>
          {/* Radar / Bar Comparison */}
          <div className={`${styles.chartCard} glass-card`}>
            <h3 className={styles.chartTitle}>Dimension Comparison</h3>
            <div className={styles.dimensionList}>
              {result.dimensions.map((dim) => (
                <div key={dim.dimension} className={styles.dimensionRow}>
                  <div className={styles.dimLabel}>{dim.label}</div>
                  <div className={styles.dimBars}>
                    {result.ideas.map((idea, idx) => {
                      const score = dim.scores[idea.id] || 0;
                      const maxScore = getMaxScore(dim);
                      const colors = [
                        "var(--accent-primary)",
                        "var(--accent-secondary)",
                        "var(--success)",
                        "var(--warning)",
                      ];
                      return (
                        <div key={idea.id} className={styles.barRow}>
                          <div className={styles.barLabel} style={{ color: colors[idx] }}>
                            {idea.title.length > 18 ? idea.title.slice(0, 18) + "…" : idea.title}
                          </div>
                          <div className={styles.barTrack}>
                            <div
                              className={styles.barFill}
                              style={{
                                width: `${(score / maxScore) * 100}%`,
                                background: colors[idx],
                              }}
                            />
                          </div>
                          <div className={styles.barValue}>{(score * 100).toFixed(0)}%</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Composite Scores */}
          <div className={`${styles.scoresCard} glass-card`}>
            <h3 className={styles.chartTitle}>Overall Scores</h3>
            <div className={styles.scoresList}>
              {result.ideas
                .map((idea) => {
                  const avg =
                    result.dimensions.reduce((sum, d) => sum + (d.scores[idea.id] || 0), 0) /
                    result.dimensions.length;
                  return { ...idea, score: avg };
                })
                .sort((a, b) => b.score - a.score)
                .map((idea, rank) => (
                  <div key={idea.id} className={styles.scoreItem}>
                    <div className={styles.scoreRank}>#{rank + 1}</div>
                    <div className={styles.scoreInfo}>
                      <div className={styles.scoreName}>{idea.title}</div>
                      <div className="progress-bar" style={{ height: 8 }}>
                        <div
                          className="progress-bar-fill"
                          style={{ width: `${idea.score * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className={styles.scoreValue}>{(idea.score * 100).toFixed(0)}%</div>
                  </div>
                ))}
            </div>
          </div>

          {/* AI Recommendation */}
          {result.recommendation && (
            <div className={`${styles.recommendation} glass-card`}>
              <h3 className={styles.chartTitle}>🤖 AI Recommendation</h3>
              <p className={styles.recText}>{result.recommendation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
