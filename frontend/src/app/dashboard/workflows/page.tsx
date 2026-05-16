"use client";

import { useState, useEffect } from "react";
import styles from "./workflows.module.css";
import { workflowsApi, type WorkflowGraph } from "@/lib/api";

export default function WorkflowsPage() {
  const [graph, setGraph] = useState<WorkflowGraph | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await workflowsApi.getGraph();
        setGraph(data);
      } catch {
        setGraph(null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const getNodeStatus = (nodeId: string) => {
    if (!graph?.current_node) return "pending";
    const nodeOrder = graph.nodes.map((n) => n.id);
    const currentIdx = nodeOrder.indexOf(graph.current_node);
    const thisIdx = nodeOrder.indexOf(nodeId);
    if (thisIdx < currentIdx) return "completed";
    if (thisIdx === currentIdx) return "active";
    return "pending";
  };

  const getNodeEmoji = (type: string) => {
    const map: Record<string, string> = {
      agent: "🤖", decision: "⚡", process: "⚙️", terminal: "🏁", error: "⚠️",
    };
    return map[type] || "📦";
  };

  return (
    <div className="animate-fade-in">
      <p className={styles.subtitle}>Visualize the LangGraph incubation state machine and its current state.</p>

      <div className={`${styles.graphContainer} glass-card`}>
        <div className={styles.graphHeader}>
          <h3>Incubation Workflow</h3>
          <div className={styles.legend}>
            <span className={styles.legendItem}><span className={`${styles.dot} ${styles.dotCompleted}`} /> Completed</span>
            <span className={styles.legendItem}><span className={`${styles.dot} ${styles.dotActive}`} /> Active</span>
            <span className={styles.legendItem}><span className={`${styles.dot} ${styles.dotPending}`} /> Pending</span>
          </div>
        </div>

        {loading ? (
          <div className={styles.flowGrid}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={styles.node}>
                <div className="skeleton" style={{ width: 40, height: 40, borderRadius: "50%" }} />
                <div className="skeleton" style={{ height: 14, width: 80, marginTop: 8 }} />
              </div>
            ))}
          </div>
        ) : graph ? (
          <div className={styles.flowGrid}>
            {graph.nodes.map((node) => {
              const status = getNodeStatus(node.id);
              return (
                <div
                  key={node.id}
                  className={`${styles.node} ${styles[`node_${status}`]} ${styles[`nodeType_${node.type}`]}`}
                >
                  <div className={styles.nodeIcon}>{getNodeEmoji(node.type)}</div>
                  <div className={styles.nodeLabel}>{node.label}</div>
                  <div className={styles.nodeType}>{node.type}</div>
                  <div className={styles.nodeDesc}>{node.description}</div>
                </div>
              );
            })}
          </div>
        ) : (
          <p style={{ color: "var(--text-muted)", padding: "var(--space-8)", textAlign: "center" }}>
            Could not load workflow graph. Is the backend running?
          </p>
        )}
      </div>

      {/* Edge Map */}
      {graph && (
        <div className={`${styles.decisionLog} glass-card`}>
          <h3>Workflow Transitions</h3>
          <div className={styles.logEntries}>
            {graph.edges.map((edge, i) => (
              <div key={i} className={styles.logEntry}>
                <span className="badge badge-accent">{edge.from}</span>
                <span className={styles.logArrow}>→</span>
                <span className="badge badge-info">{edge.to}</span>
                {edge.label && <span className={styles.logText}>{edge.label}</span>}
                {edge.type && <span className={`badge ${edge.type === "conditional" ? "badge-warning" : "badge-success"}`}>{edge.type}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
