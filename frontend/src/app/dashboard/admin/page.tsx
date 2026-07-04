"use client";

import styles from "./admin.module.css";
import { useAuth } from "@/components/AuthProvider";

export default function AdminDashboardPage() {
  const { user } = useAuth();

  return (
    <div className="animate-fade-in">
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.headerIcon}>👑</div>
          <div>
            <h1 className={styles.pageTitle}>Admin Dashboard</h1>
            <p className={styles.pageSubtitle}>Platform overview & control</p>
          </div>
        </div>
      </div>
      
      <div className="glass-card" style={{ padding: "var(--space-8)", textAlign: "center", marginTop: "var(--space-6)" }}>
        <h2 style={{ color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>
          Admin Panel Unavailable
        </h2>
        <p style={{ color: "var(--text-secondary)", maxWidth: 500, margin: "0 auto var(--space-6)" }}>
          The multi-tenant admin console is currently disabled in single-user mode.
        </p>
      </div>
    </div>
  );
}
