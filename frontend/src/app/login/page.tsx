"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import styles from "./auth.module.css";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // Attempt Supabase auth if configured
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
      if (supabaseUrl) {
        const { createClient } = await import("@/lib/supabase/client");
        const supabase = createClient();
        const { error: authError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (authError) {
          setError(authError.message);
          setLoading(false);
          return;
        }
      }
      router.push("/dashboard");
    } catch {
      // Fallback: allow demo login when Supabase is not configured
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = () => {
    router.push("/dashboard");
  };

  return (
    <div className={styles.authPage}>
      {/* Floating orbs */}
      <div className={styles.orbTop} />
      <div className={styles.orbBottom} />

      <div className={`${styles.authCard} glass-card animate-fade-in`}>
        <div className={styles.logoContainer}>
          <div className={styles.logo}>🚀</div>
          <div className={styles.logoGlow} />
        </div>
        <h1 className={styles.title}>Welcome Back</h1>
        <p className={styles.subtitle}>Sign in to your AI Incubator account</p>

        {error && (
          <div className={styles.errorBanner}>
            <span>⚠️</span> {error}
          </div>
        )}

        <form onSubmit={handleLogin} className={styles.form}>
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="login-email">Email</label>
            <input
              id="login-email"
              className="input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div className={styles.fieldGroup}>
            <div className={styles.labelRow}>
              <label className="input-label" htmlFor="login-password">Password</label>
              <Link href="/login" className={styles.forgotLink}>Forgot?</Link>
            </div>
            <input
              id="login-password"
              className="input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            style={{ width: "100%" }}
            disabled={loading}
            id="login-btn"
          >
            {loading ? (
              <><span className="loader" /> Signing in...</>
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <div className={styles.divider}>
          <span>or</span>
        </div>

        <button
          onClick={handleDemoLogin}
          className={`btn btn-secondary ${styles.demoBtn}`}
          id="demo-login-btn"
        >
          ⚡ Continue as Demo User
        </button>

        <p className={styles.altLink}>
          Don&apos;t have an account?{" "}
          <Link href="/signup">Create Account</Link>
        </p>

        <div className={styles.features}>
          <div className={styles.featureItem}>
            <span>🔬</span> 5 AI Research Agents
          </div>
          <div className={styles.featureItem}>
            <span>🎯</span> Investor Pitch Simulation
          </div>
          <div className={styles.featureItem}>
            <span>📊</span> Full Analysis Reports
          </div>
        </div>
      </div>
    </div>
  );
}
