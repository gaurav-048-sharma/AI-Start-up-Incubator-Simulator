"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "./auth.module.css";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    // In production: supabase.auth.signInWithPassword({ email, password })
    setTimeout(() => { setLoading(false); window.location.href = "/dashboard"; }, 1000);
  };

  return (
    <div className={styles.authPage}>
      <div className={`${styles.authCard} glass-card animate-fade-in`}>
        <div className={styles.logo}>🚀</div>
        <h1 className={styles.title}>Welcome Back</h1>
        <p className={styles.subtitle}>Sign in to your AI Incubator account</p>

        <form onSubmit={handleLogin} className={styles.form}>
          <div>
            <label className="input-label" htmlFor="login-email">Email</label>
            <input id="login-email" className="input" type="email" placeholder="you@example.com"
              value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="input-label" htmlFor="login-password">Password</label>
            <input id="login-password" className="input" type="password" placeholder="••••••••"
              value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button type="submit" className="btn btn-primary btn-lg" style={{ width: "100%" }} disabled={loading} id="login-btn">
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className={styles.altLink}>
          Don&apos;t have an account? <Link href="/signup">Sign Up</Link>
        </p>
      </div>
    </div>
  );
}
