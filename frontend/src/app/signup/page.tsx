"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "./auth.module.css";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => { setLoading(false); window.location.href = "/dashboard"; }, 1000);
  };

  return (
    <div className={styles.authPage}>
      <div className={`${styles.authCard} glass-card animate-fade-in`}>
        <div className={styles.logo}>🚀</div>
        <h1 className={styles.title}>Create Account</h1>
        <p className={styles.subtitle}>Start incubating your startup ideas with AI</p>

        <form onSubmit={handleSignup} className={styles.form}>
          <div>
            <label className="input-label" htmlFor="signup-name">Full Name</label>
            <input id="signup-name" className="input" placeholder="John Doe"
              value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <label className="input-label" htmlFor="signup-email">Email</label>
            <input id="signup-email" className="input" type="email" placeholder="you@example.com"
              value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="input-label" htmlFor="signup-password">Password</label>
            <input id="signup-password" className="input" type="password" placeholder="••••••••"
              value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button type="submit" className="btn btn-primary btn-lg" style={{ width: "100%" }} disabled={loading} id="signup-btn">
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className={styles.altLink}>
          Already have an account? <Link href="/login">Sign In</Link>
        </p>
      </div>
    </div>
  );
}
