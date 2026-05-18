"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "../login/auth.module.css";
import { createClient } from "@/lib/supabase/client";

export default function ResetPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const supabase = createClient();
      if (!supabase) {
        throw new Error("Authentication is not configured in this environment.");
      }
      const { error: authError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/update-password`,
      });
      
      if (authError) {
        setError(authError.message);
      } else {
        setSuccess(true);
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred");
      }
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
            <div className={styles.logo}>✉️</div>
            <div className={styles.logoGlow} />
          </div>
          <h1 className={styles.title}>Check Your Email</h1>
          <p className={styles.subtitle}>
            We sent a password reset link to <strong>{email}</strong>.
          </p>
          <Link href="/login" className="btn btn-primary btn-lg" style={{ width: "100%", marginTop: "var(--space-4)" }}>
            Return to Sign In
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
          <div className={styles.logo}>🔐</div>
          <div className={styles.logoGlow} />
        </div>
        <h1 className={styles.title}>Reset Password</h1>
        <p className={styles.subtitle}>Enter your email to receive a reset link</p>

        {error && (
          <div className={styles.errorBanner}>
            <span>⚠️</span> {error}
          </div>
        )}

        <form onSubmit={handleReset} className={styles.form}>
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="reset-email">Email</label>
            <input
              id="reset-email"
              className="input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={loading || !email}
            style={{ width: "100%" }}
          >
            {loading ? (
              <span className={styles.loadingSpinner} />
            ) : (
              "Send Reset Link"
            )}
          </button>
        </form>

        <div className={styles.formFooter}>
          <Link href="/login" className={styles.footerLink}>
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
