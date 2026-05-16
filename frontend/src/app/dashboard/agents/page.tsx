"use client";

import { useState, useEffect } from "react";
import styles from "./agents.module.css";
import { agentsApi, type AgentRole } from "@/lib/api";

const AGENT_META: Record<string, { icon: string; fullRole: string }> = {
  market_analyst: { icon: "🔬", fullRole: "Senior Market Research Analyst" },
  tech_architect: { icon: "🏗️", fullRole: "Chief Technology Architect" },
  growth_strategist: { icon: "🚀", fullRole: "VP of Growth Strategy" },
  financial_analyst: { icon: "💹", fullRole: "Startup CFO Advisor" },
  legal_advisor: { icon: "⚖️", fullRole: "IP & Compliance Advisor" },
};

export default function AgentsPage() {
  const [roles, setRoles] = useState<AgentRole[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await agentsApi.getRoles();
        setRoles(data.roles || []);
      } catch {
        setRoles([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="animate-fade-in">
      <p className={styles.subtitle}>Monitor AI agents working on your startup ideas in real-time.</p>

      <div className={`${styles.agentsGrid} stagger-children`}>
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={`${styles.agentCard} glass-card`}>
              <div className={styles.cardHeader}>
                <div className="skeleton" style={{ height: 20, width: "50%" }} />
                <div className="skeleton" style={{ height: 20, width: 60 }} />
              </div>
              <div className={styles.cardBody}>
                <div className="skeleton" style={{ height: 14, width: "80%" }} />
              </div>
            </div>
          ))
        ) : (
          roles.map((role) => {
            const meta = AGENT_META[role.id] || { icon: "🤖", fullRole: role.name };
            return (
              <div key={role.id} className={`${styles.agentCard} glass-card`}>
                <div className={styles.cardHeader}>
                  <div className={styles.agentInfo}>
                    <span className={styles.agentIcon}>{meta.icon}</span>
                    <div>
                      <div className={styles.agentName}>{role.name}</div>
                      <div className={styles.agentRole}>{meta.fullRole}</div>
                    </div>
                  </div>
                  <span className="badge badge-success">ready</span>
                </div>
                <div className={styles.cardBody}>
                  <div className={styles.fieldLabel}>Capabilities</div>
                  <div className={styles.fieldValue}>{role.description}</div>
                </div>
                <div className={styles.cardFooter}>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Status</span>
                    <span className={styles.metricValue}>Available</span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Provider</span>
                    <span className={styles.metricValue}>OpenAI</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
