"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import styles from "../login/auth.module.css";
import { createClient } from "@/lib/supabase/client";

export default function UpdatePasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // Supabase will automatically parse the hash fragment and set the session
    // We just wait a tick to ensure the session is established.
    const checkSession = async () => {
      const supabase = createClient();
      if (!supabase) {
        setIsReady(true);
        return;
      }
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        setError("Invalid or expired password reset link.");
      }
      setIsReady(true);
    };
    checkSession();
  }, []);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      setLoading(false);
      return;
    }

    try {
      const supabase = createClient();
      if (!supabase) {
        throw new Error("Authentication is not configured in this environment.");
      }
      const { error: authError } = await supabase.auth.updateUser({
        password: password,
      });
      
      if (authError) {
        setError(authError.message);
      } else {
        setSuccess(true);
        setTimeout(() => {
          router.push("/dashboard");
        }, 2000);
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

  if (!isReady) {
    return <div className="flex items-center justify-center min-h-screen bg-black text-white">Validating link...</div>;
  }

  return (
    <div className={styles.authPage}>
      <div className={styles.orbTop} />
      <div className={styles.orbBottom} />

      <div className={`${styles.authCard} glass-card animate-fade-in`}>
        <div className={styles.logoContainer}>
          <div className={styles.logo}>🔑</div>
          <div className={styles.logoGlow} />
        </div>
        <h1 className={styles.title}>Update Password</h1>
        
        {success ? (
          <div style={{ textAlign: "center" }}>
            <p className={styles.subtitle} style={{ color: "#10b981", fontWeight: "bold" }}>
              Password updated successfully!
            </p>
            <p className={styles.subtitle}>Redirecting to dashboard...</p>
          </div>
        ) : (
          <>
            <p className={styles.subtitle}>Enter your new password below.</p>
            
            {error && (
              <div className={styles.errorBanner}>
                <span>⚠️</span> {error}
              </div>
            )}

            <form onSubmit={handleUpdate} className={styles.form}>
              <div className={styles.fieldGroup}>
                <label className="input-label" htmlFor="new-password">New Password</label>
                <input
                  id="new-password"
                  className="input"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  disabled={!!error && error.includes("expired")}
                />
              </div>
              
              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={loading || !password || (!!error && error.includes("expired"))}
                style={{ width: "100%" }}
              >
                {loading ? (
                  <span className={styles.loadingSpinner} />
                ) : (
                  "Update Password"
                )}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
