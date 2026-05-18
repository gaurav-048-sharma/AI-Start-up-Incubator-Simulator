"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./auth.module.css";

export default function SignupPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get("next") || "/dashboard";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      setLoading(false);
      return;
    }

    try {
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
      if (supabaseUrl) {
        const { createClient } = await import("@/lib/supabase/client");
        const supabase = createClient();
        const { error: authError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { full_name: name, role: "founder_product_lead" },
          },
        });
        if (authError) {
          setError(authError.message);
          setLoading(false);
          return;
        }
        setSuccess(true);
        return;
      }
      router.push(nextUrl);
    } catch {
      router.push(nextUrl);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className={styles.authPage}>
        <div className={styles.orbTop} />
        <div className={styles.orbBottom} />
        <div className={`${styles.authCard} glass-card animate-fade-in`}>
          <div className={styles.logoContainer}>
            <div className={styles.logo}>✅</div>
            <div className={styles.logoGlow} />
          </div>
          <h1 className={styles.title}>Check Your Email</h1>
          <p className={styles.subtitle}>
            We sent a confirmation link to <strong>{email}</strong>.
            Click it to activate your account.
          </p>
          <Link href="/login" className="btn btn-primary btn-lg" style={{ width: "100%", marginTop: "var(--space-4)" }}>
            Go to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.authPage}>
      <div className={styles.orbTop} />
      <div className={styles.orbBottom} />

      <div className={`${styles.authCard} glass-card animate-fade-in`}>
        <div className={styles.logoContainer}>
          <div className={styles.logo}>🚀</div>
          <div className={styles.logoGlow} />
        </div>
        <h1 className={styles.title}>Create Account</h1>
        <p className={styles.subtitle}>Start incubating your startup ideas with AI</p>

        {error && (
          <div className={styles.errorBanner}>
            <span>⚠️</span> {error}
          </div>
        )}

        <form onSubmit={handleSignup} className={styles.form}>
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="signup-name">Full Name</label>
            <input
              id="signup-name"
              className="input"
              placeholder="Jane Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoComplete="name"
            />
          </div>
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="signup-email">Email</label>
            <input
              id="signup-email"
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
            <label className="input-label" htmlFor="signup-password">Password</label>
            <input
              id="signup-password"
              className="input"
              type="password"
              placeholder="Min 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete="new-password"
            />
            <div className={styles.passwordStrength}>
              <div
                className={styles.passwordBar}
                style={{
                  width: `${Math.min(100, (password.length / 12) * 100)}%`,
                  background: password.length < 6
                    ? "var(--error)"
                    : password.length < 10
                    ? "var(--warning)"
                    : "var(--success)",
                }}
              />
            </div>
          </div>
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            style={{ width: "100%" }}
            disabled={loading}
            id="signup-btn"
          >
            {loading ? (
              <><span className="loader" /> Creating account...</>
            ) : (
              "Create Account"
            )}
          </button>
        </form>

        <p className={styles.altLink}>
          Already have an account?{" "}
          <Link href="/login">Sign In</Link>
        </p>

        <p className={styles.altLink} style={{ marginTop: "var(--space-2)" }}>
          Need a workspace for your team?{" "}
          <Link href="/enterprise">Request Enterprise Access</Link>
        </p>

        <p className={styles.terms}>
          By creating an account, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}
