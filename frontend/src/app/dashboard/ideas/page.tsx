"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import styles from "./ideas.module.css";
import { ideasApi, type Idea } from "@/lib/api";

export default function IdeasPage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);

  useEffect(() => {
    // Initial load of org ID from localStorage
    const stored = typeof window !== "undefined" ? localStorage.getItem("activeOrgId") : null;
    setActiveOrgId(stored);

    // Listen for changes (e.g. from DashboardLayout sidebar)
    const handleStorage = () => {
      const current = localStorage.getItem("activeOrgId");
      setActiveOrgId(current);
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  useEffect(() => {
    async function load() {
      if (!activeOrgId && typeof window !== "undefined" && !localStorage.getItem("activeOrgId")) {
        // If we really don't have an org yet, show loading or empty
        setLoading(false);
        return;
      }
      
      setLoading(true);
      try {
        const data = await ideasApi.list();
        setIdeas(data.ideas || []);
      } catch {
        setIdeas([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activeOrgId]);

  return (
    <div className="animate-fade-in">
      <div className={styles.header}>
        <p className={styles.subtitle}>Track and manage all your startup ideas in one place.</p>
        <Link href="/dashboard/ideas/new" className="btn btn-primary" id="ideas-new-btn">
          ✨ Submit New Idea
        </Link>
      </div>

      <div className={`${styles.ideasGrid} stagger-children`}>
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className={`${styles.card} glass-card`}>
              <div className="skeleton" style={{ height: 20, width: "60%", marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 14, width: "100%", marginBottom: 4 }} />
              <div className="skeleton" style={{ height: 14, width: "80%" }} />
            </div>
          ))
        ) : ideas.length > 0 ? (
          <>
            {ideas.map((idea) => (
              <Link key={idea.id} href={`/dashboard/ideas/${idea.id}`} className={`${styles.card} glass-card`}>
                <div className={styles.cardHeader}>
                  <span className={`badge ${getStatusBadge(idea.status)}`}>{idea.status}</span>
                  <span className={styles.cardDate}>{new Date(idea.created_at).toLocaleDateString()}</span>
                </div>
                <h3 className={styles.cardTitle}>{idea.title}</h3>
                <p className={styles.cardDesc}>{idea.description}</p>
                <div className={styles.cardFooter}>
                  {idea.industry && <span className="badge badge-accent">{idea.industry}</span>}
                  <div className={styles.progressWrap}>
                    <span className={styles.progressText}>{idea.progress}%</span>
                    <div className="progress-bar" style={{ width: "100px" }}>
                      <div className="progress-bar-fill" style={{ width: `${idea.progress}%` }} />
                    </div>
                  </div>
                </div>
              </Link>
            ))}
            <Link href="/dashboard/ideas/new" className={`${styles.emptyCard} glass-card`}>
              <div className={styles.emptyIcon}>+</div>
              <div className={styles.emptyText}>Add New Idea</div>
            </Link>
          </>
        ) : (
          <div className={`${styles.emptyCard} glass-card`} style={{ gridColumn: "1 / -1" }}>
            <div className={styles.emptyIcon}>💡</div>
            <div className={styles.emptyText}>No ideas yet — submit your first one!</div>
            <Link href="/dashboard/ideas/new" className="btn btn-primary btn-sm" style={{ marginTop: 12 }}>
              ✨ Submit New Idea
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

function getStatusBadge(status: string): string {
  const map: Record<string, string> = {
    completed: "badge-success", researching: "badge-info",
    submitted: "badge-info", validating: "badge-info",
    planning: "badge-info", simulating: "badge-warning",
    draft: "badge-accent", failed: "badge-error",
  };
  return map[status] || "badge-accent";
}
