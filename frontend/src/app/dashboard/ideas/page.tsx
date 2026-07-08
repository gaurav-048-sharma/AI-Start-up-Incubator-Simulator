"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import styles from "./ideas.module.css";
import { ideasApi, type Idea } from "@/lib/api";

export default function IdeasPage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load(isInitial = false) {
      if (isInitial) setLoading(true);
      try {
        const data = await ideasApi.list();
        if (mounted) setIdeas(data.ideas || []);
      } catch {
        if (mounted && isInitial) setIdeas([]);
      } finally {
        if (mounted && isInitial) setLoading(false);
      }
    }
    load(true);

    const interval = setInterval(() => {
      load(false);
    }, 3000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

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
                  <span className={`badge ${getStatusBadge(idea.status)}`} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {!['completed', 'failed', 'draft'].includes(idea.status) && (
                      <span className="loader" style={{ width: 12, height: 12, borderWidth: 2 }} />
                    )}
                    {idea.status}
                  </span>
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
