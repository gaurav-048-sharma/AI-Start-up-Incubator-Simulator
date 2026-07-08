"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import styles from "./auth.module.css";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get("next") || "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Failed to log in");
      }
      
      // Save JWT token
      localStorage.setItem("access_token", data.access_token);
      
      // Redirect
      window.location.href = nextUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.authPage}>
      <div className={styles.orbTop} />
      <div className={styles.orbBottom} />
      <div className={`${styles.authCard} glass-card animate-fade-in`}>
        <div className={styles.logoContainer}>
          <div className={styles.logo}>🚀</div>
          <div className={styles.logoGlow} />
        </div>
        <h1 className={styles.title}>Welcome Back</h1>
        <p className={styles.subtitle}>Sign in to your AI Incubator account</p>

        {error && <div className={styles.errorBanner}>⚠️ {error}</div>}

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
              autoFocus
              suppressHydrationWarning
            />
          </div>
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="login-password">Password</label>
            <input
              id="login-password"
              className="input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary btn-lg" style={{ width: "100%" }} disabled={loading}>
            {loading ? <><span className="loader" /> Signing in...</> : "Sign In"}
          </button>

          <div style={{ marginTop: "1rem", textAlign: "center", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
            Don't have an account? <Link href="/signup" style={{ color: "var(--primary)" }}>Sign up</Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className={styles.authPage}><div className="loader" /></div>}>
      <LoginForm />
    </Suspense>
  );
}
