"use client";

import styles from "./team.module.css";
import { useAuth } from "@/components/AuthProvider";

export default function TeamPage() {
  const { user } = useAuth();

  return (
    <div className="animate-fade-in">
      <div className="glass-card" style={{ padding: "var(--space-8)", textAlign: "center" }}>
        <div style={{ fontSize: "4rem", marginBottom: "var(--space-4)" }}>👤</div>
        <h2 style={{ color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>
          Single User Mode
        </h2>
        <p style={{ color: "var(--text-secondary)", maxWidth: 500, margin: "0 auto var(--space-6)" }}>
          You&apos;re currently the sole founder on this platform. Team management and organizations 
          will be available in a future update.
        </p>
        
        <div className="glass-card" style={{ display: "inline-block", padding: "var(--space-4) var(--space-6)", marginTop: "var(--space-4)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div style={{ width: 48, height: 48, borderRadius: "50%", background: "var(--accent-primary)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.5rem" }}>
              🚀
            </div>
            <div style={{ textAlign: "left" }}>
              <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{user?.email || "Founder"}</div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Founder · Enterprise Tier</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
