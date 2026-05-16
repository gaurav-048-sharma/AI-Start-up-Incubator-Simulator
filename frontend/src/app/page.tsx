import Link from "next/link";
import styles from "./page.module.css";

export default function LandingPage() {
  return (
    <div className={styles.landing}>
      {/* ── Hero Section ─────────────────────────────────────── */}
      <section className={styles.hero} id="hero">
        <div className={styles.heroBadge}>
          <span className={styles.heroBadgeDot} />
          AI-Powered Startup Accelerator
        </div>

        <h1 className={styles.heroTitle}>
          Transform Ideas into{" "}
          <span className="text-gradient">Investor-Ready</span>{" "}
          Businesses with AI
        </h1>

        <p className={styles.heroSubtitle}>
          Submit your startup idea and watch autonomous AI agents conduct market research,
          design architecture, build financial models, and pitch to virtual investors —
          all in real-time.
        </p>

        <div className={styles.heroActions}>
          <Link href="/dashboard" className="btn btn-primary btn-lg" id="cta-dashboard">
            🚀 Launch Dashboard
          </Link>
          <Link href="/dashboard/ideas/new" className="btn btn-secondary btn-lg" id="cta-submit">
            Submit an Idea
          </Link>
        </div>

        <div className={styles.heroStats}>
          <div className={styles.heroStat}>
            <div className={styles.heroStatValue}>5</div>
            <div className={styles.heroStatLabel}>AI Agents</div>
          </div>
          <div className={styles.heroStat}>
            <div className={styles.heroStatValue}>7</div>
            <div className={styles.heroStatLabel}>Research Reports</div>
          </div>
          <div className={styles.heroStat}>
            <div className={styles.heroStatValue}>3</div>
            <div className={styles.heroStatLabel}>Investor Personas</div>
          </div>
          <div className={styles.heroStat}>
            <div className={styles.heroStatValue}>∞</div>
            <div className={styles.heroStatLabel}>Startup Ideas</div>
          </div>
        </div>
      </section>

      {/* ── Features Section ─────────────────────────────────── */}
      <section className={styles.features} id="features">
        <div className={styles.sectionHeader}>
          <div className={styles.sectionLabel}>How It Works</div>
          <h2 className={styles.sectionTitle}>
            Your AI Founding Team, Ready to Build
          </h2>
          <p className={styles.sectionSubtitle}>
            Six phases of autonomous research, validation, and execution — from raw idea to pitch-ready startup.
          </p>
        </div>

        <div className={`${styles.featuresGrid} stagger-children`}>
          <div className={`${styles.featureCard} glass-card`}>
            <div className={styles.featureIcon}>🔍</div>
            <h3 className={styles.featureTitle}>Market Research</h3>
            <p className={styles.featureDesc}>
              AI agents analyze TAM/SAM/SOM, map competitors, identify trends, and validate your market opportunity with real data.
            </p>
          </div>

          <div className={`${styles.featureCard} glass-card`}>
            <div className={styles.featureIcon}>⚙️</div>
            <h3 className={styles.featureTitle}>Tech Architecture</h3>
            <p className={styles.featureDesc}>
              Get a complete technical blueprint — stack recommendations, scalability plans, MVP specs, and infrastructure cost estimates.
            </p>
          </div>

          <div className={`${styles.featureCard} glass-card`}>
            <div className={styles.featureIcon}>📈</div>
            <h3 className={styles.featureTitle}>Growth Strategy</h3>
            <p className={styles.featureDesc}>
              Data-driven GTM plans, pricing models, acquisition channels, and growth loop design tailored to your startup.
            </p>
          </div>

          <div className={`${styles.featureCard} glass-card`}>
            <div className={styles.featureIcon}>💰</div>
            <h3 className={styles.featureTitle}>Financial Projections</h3>
            <p className={styles.featureDesc}>
              3-year revenue models, unit economics, burn rate analysis, and funding strategy with investor-grade precision.
            </p>
          </div>

          <div className={`${styles.featureCard} glass-card`}>
            <div className={styles.featureIcon}>⚖️</div>
            <h3 className={styles.featureTitle}>Legal & IP Review</h3>
            <p className={styles.featureDesc}>
              Patent landscape analysis, regulatory compliance mapping, and corporate structure recommendations.
            </p>
          </div>

          <div className={`${styles.featureCard} glass-card`}>
            <div className={styles.featureIcon}>🎯</div>
            <h3 className={styles.featureTitle}>Investor Simulation</h3>
            <p className={styles.featureDesc}>
              Pitch to AI investor agents — a VC partner, angel investor, and strategic CVC — with real-time Q&A and feedback.
            </p>
          </div>
        </div>
      </section>

      {/* ── Agents Section ───────────────────────────────────── */}
      <section className={styles.agents} id="agents">
        <div className={styles.sectionHeader}>
          <div className={styles.sectionLabel}>Meet Your Team</div>
          <h2 className={styles.sectionTitle}>5 Specialized AI Agents</h2>
          <p className={styles.sectionSubtitle}>
            Each agent brings deep domain expertise to research, validate, and refine your startup.
          </p>
        </div>

        <div className={`${styles.agentsGrid} stagger-children`}>
          {[
            { emoji: "🔬", name: "Market Analyst", role: "McKinsey-trained researcher" },
            { emoji: "🏗️", name: "Tech Architect", role: "CTO-level system designer" },
            { emoji: "🚀", name: "Growth Strategist", role: "VP Growth from Notion/Figma" },
            { emoji: "💹", name: "Financial Analyst", role: "Ex-Sequoia financial modeler" },
            { emoji: "⚖️", name: "Legal Advisor", role: "Wilson Sonsini IP counsel" },
          ].map((agent) => (
            <div key={agent.name} className={`${styles.agentCard} glass-card`}>
              <div className={styles.agentAvatar}>{agent.emoji}</div>
              <div className={styles.agentName}>{agent.name}</div>
              <div className={styles.agentRole}>{agent.role}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA Section ──────────────────────────────────────── */}
      <section className={styles.cta} id="cta">
        <div className={`${styles.ctaCard} glass-card animate-pulse-glow`}>
          <h2 className={styles.ctaTitle}>Ready to Incubate Your Idea?</h2>
          <p className={styles.ctaSubtitle}>
            Let AI agents do the heavy lifting. Get market research, tech plans, and investor feedback in minutes.
          </p>
          <Link href="/dashboard/ideas/new" className="btn btn-primary btn-lg" id="cta-bottom">
            🚀 Start Building Now
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className={styles.footer}>
        <p>
          AI Start-up Incubator Simulator — Powered by CrewAI, LangGraph & AutoGen
        </p>
      </footer>
    </div>
  );
}
