"use client";

import { useState } from "react";
import styles from "./simulation.module.css";

const INVESTORS = [
  { name: "Sarah Chen", firm: "Horizon Ventures", role: "VC Partner", style: "Analytical", avatar: "👩‍💼" },
  { name: "Marcus Johnson", firm: "Independent", role: "Angel Investor", style: "Visionary", avatar: "👨‍💻" },
  { name: "Dr. Priya Patel", firm: "TechCorp Ventures", role: "Strategic CVC", style: "Technical", avatar: "👩‍🔬" },
];

const MOCK_TRANSCRIPT = [
  { speaker: "Founder", role: "founder", content: "Thank you for your time today. We're building an AI-powered resume builder that transforms how job seekers create tailored applications..." },
  { speaker: "Sarah Chen", role: "investor", content: "Interesting concept. What's your current TAM and how did you arrive at those numbers? Also, what does your competitive landscape look like?" },
  { speaker: "Founder", role: "founder", content: "Our TAM is $4.2B based on the global recruitment software market. We've identified 8 direct competitors, but none offer real-time AI customization per job posting..." },
  { speaker: "Marcus Johnson", role: "investor", content: "I love the vision. Tell me about your founding story — what personal experience led you to this problem?" },
];

export default function SimulationPage() {
  const [isRunning, setIsRunning] = useState(false);

  return (
    <div className="animate-fade-in">
      <p className={styles.subtitle}>Pitch your startup to AI investor agents and receive real-time feedback.</p>

      {/* Investor Panel */}
      <div className={styles.investorPanel}>
        <h3 className={styles.panelTitle}>Investor Panel</h3>
        <div className={styles.investorGrid}>
          {INVESTORS.map((inv) => (
            <div key={inv.name} className={`${styles.investorCard} glass-card`}>
              <div className={styles.investorAvatar}>{inv.avatar}</div>
              <div className={styles.investorName}>{inv.name}</div>
              <div className={styles.investorFirm}>{inv.firm}</div>
              <div className={styles.investorMeta}>
                <span className="badge badge-accent">{inv.role}</span>
                <span className="badge badge-info">{inv.style}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Interface */}
      <div className={`${styles.chatContainer} glass-card`}>
        <div className={styles.chatHeader}>
          <h3>Pitch Session</h3>
          <button className="btn btn-primary btn-sm" id="start-pitch-btn"
            onClick={() => setIsRunning(!isRunning)}>
            {isRunning ? "⏸ Pause" : "▶ Start Pitch"}
          </button>
        </div>

        <div className={styles.chatMessages}>
          {MOCK_TRANSCRIPT.map((msg, i) => (
            <div key={i} className={`${styles.message} ${msg.role === "founder" ? styles.messageFounder : styles.messageInvestor}`}>
              <div className={styles.messageSpeaker}>
                {msg.role === "founder" ? "🚀" : "💼"} {msg.speaker}
              </div>
              <div className={styles.messageContent}>{msg.content}</div>
            </div>
          ))}

          {isRunning && (
            <div className={styles.typingWrap}>
              <span className={styles.typingLabel}>Dr. Priya Patel is typing</span>
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          )}
        </div>

        <div className={styles.chatInput}>
          <input className="input" placeholder="Type your response as the founder..." id="founder-input" />
          <button className="btn btn-primary" id="send-response-btn">Send</button>
        </div>
      </div>
    </div>
  );
}
