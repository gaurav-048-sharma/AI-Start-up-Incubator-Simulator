"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./auth.module.css";

type MfaStep = "login" | "mfa_verify";

interface MfaFactorInfo {
  id: string;
  friendly_name?: string;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get("next") || "/dashboard";
  const mfaParam = searchParams.get("mfa");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // MFA state
  const [step, setStep] = useState<MfaStep>(mfaParam === "required" ? "mfa_verify" : "login");
  const [mfaCode, setMfaCode] = useState(["", "", "", "", "", ""]);
  const [mfaFactor, setMfaFactor] = useState<MfaFactorInfo | null>(null);
  const [mfaLoading, setMfaLoading] = useState(false);
  const codeInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // If user lands on ?mfa=required, pre-load their MFA factor
  useEffect(() => {
    if (mfaParam === "required") {
      loadMfaFactors();
    }
  }, [mfaParam]);

  const loadMfaFactors = async () => {
    try {
      const { createClient } = await import("@/lib/supabase/client");
      const supabase = createClient();
      if (!supabase) return;

      const { data } = await supabase.auth.mfa.listFactors();
      if (data?.totp && data.totp.length > 0) {
        const verifiedFactor = data.totp.find((f: { status: string }) => f.status === "verified");
        if (verifiedFactor) {
          setMfaFactor({ id: verifiedFactor.id, friendly_name: verifiedFactor.friendly_name });
          setStep("mfa_verify");
        }
      }
    } catch {
      // silent
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
      if (supabaseUrl) {
        const { createClient } = await import("@/lib/supabase/client");
        const supabase = createClient();
        if (!supabase) {
          throw new Error("Authentication is not configured.");
        }
        const { error: authError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (authError) {
          setError(authError.message);
          setLoading(false);
          return;
        }

        // Check MFA assurance level after password login
        const { data: aalData } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
        
        if (aalData?.currentLevel === "aal1" && aalData?.nextLevel === "aal2") {
          // User has MFA enrolled — need to verify
          const { data: factorsData } = await supabase.auth.mfa.listFactors();
          if (factorsData?.totp && factorsData.totp.length > 0) {
            const verifiedFactor = factorsData.totp.find((f: { status: string }) => f.status === "verified");
            if (verifiedFactor) {
              setMfaFactor({ id: verifiedFactor.id, friendly_name: verifiedFactor.friendly_name });
              setStep("mfa_verify");
              setLoading(false);
              return;
            }
          }
        }

        // No MFA needed — proceed to dashboard
        router.push(nextUrl);
        return;
      }
      router.push(nextUrl);
    } catch {
      router.push(nextUrl);
    } finally {
      setLoading(false);
    }
  };

  const handleMfaVerify = async () => {
    const code = mfaCode.join("");
    if (code.length !== 6) {
      setError("Please enter a complete 6-digit code");
      return;
    }

    if (!mfaFactor) {
      setError("No MFA factor found. Please log in again.");
      return;
    }

    setMfaLoading(true);
    setError("");

    try {
      const { createClient } = await import("@/lib/supabase/client");
      const supabase = createClient();
      if (!supabase) throw new Error("Auth not configured");

      // Create challenge
      const { data: challengeData, error: challengeError } = await supabase.auth.mfa.challenge({
        factorId: mfaFactor.id,
      });

      if (challengeError || !challengeData) {
        setError("Failed to create MFA challenge. Please try again.");
        setMfaLoading(false);
        return;
      }

      // Verify challenge with TOTP code
      const { data: verifyData, error: verifyError } = await supabase.auth.mfa.verify({
        factorId: mfaFactor.id,
        challengeId: challengeData.id,
        code,
      });

      if (verifyError) {
        setError("Invalid verification code. Please check your authenticator app.");
        setMfaCode(["", "", "", "", "", ""]);
        codeInputRefs.current[0]?.focus();
        setMfaLoading(false);
        return;
      }

      if (verifyData) {
        // Session upgraded to aal2 — redirect to dashboard
        router.push(nextUrl);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "MFA verification failed");
      setMfaCode(["", "", "", "", "", ""]);
    } finally {
      setMfaLoading(false);
    }
  };

  // Handle individual code digit input
  const handleCodeChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return; // digits only
    
    const newCode = [...mfaCode];
    newCode[index] = value.slice(-1); // keep only last digit
    setMfaCode(newCode);

    // Auto-focus next input
    if (value && index < 5) {
      codeInputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all 6 digits entered
    if (newCode.every((d) => d !== "") && newCode.join("").length === 6) {
      setTimeout(() => handleMfaVerify(), 100);
    }
  };

  const handleCodeKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !mfaCode[index] && index > 0) {
      codeInputRefs.current[index - 1]?.focus();
    }
    if (e.key === "Enter") {
      handleMfaVerify();
    }
  };

  const handleCodePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length > 0) {
      const newCode = [...mfaCode];
      for (let i = 0; i < pasted.length; i++) {
        newCode[i] = pasted[i];
      }
      setMfaCode(newCode);
      if (pasted.length === 6) {
        setTimeout(() => handleMfaVerify(), 100);
      } else {
        codeInputRefs.current[pasted.length]?.focus();
      }
    }
  };

  const handleDemoLogin = () => {
    router.push(nextUrl);
  };

  // ── MFA Verification Step ──────────────────────────────────────
  if (step === "mfa_verify") {
    return (
      <div className={styles.authPage}>
        <div className={styles.orbTop} />
        <div className={styles.orbBottom} />

        <div className={`${styles.authCard} glass-card animate-fade-in`}>
          <div className={styles.logoContainer}>
            <div className={styles.logo}>
              <span className={styles.shieldIcon}>🛡️</span>
            </div>
            <div className={styles.logoGlow} />
          </div>
          <h1 className={styles.title}>Two-Factor Verification</h1>
          <p className={styles.subtitle}>
            Enter the 6-digit code from your authenticator app
            {mfaFactor?.friendly_name && (
              <span className={styles.mfaFactorName}> ({mfaFactor.friendly_name})</span>
            )}
          </p>

          {error && (
            <div className={styles.errorBanner}>
              <span>⚠️</span> {error}
            </div>
          )}

          <div className={styles.mfaCodeContainer}>
            {mfaCode.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { codeInputRefs.current[i] = el; }}
                className={styles.mfaCodeInput}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleCodeChange(i, e.target.value)}
                onKeyDown={(e) => handleCodeKeyDown(i, e)}
                onPaste={i === 0 ? handleCodePaste : undefined}
                autoFocus={i === 0}
                disabled={mfaLoading}
                id={`mfa-code-${i}`}
                autoComplete="one-time-code"
              />
            ))}
          </div>

          <button
            onClick={handleMfaVerify}
            className="btn btn-primary btn-lg"
            style={{ width: "100%", marginTop: "var(--space-4)" }}
            disabled={mfaLoading || mfaCode.join("").length !== 6}
            id="mfa-verify-btn"
          >
            {mfaLoading ? (
              <><span className="loader" /> Verifying...</>
            ) : (
              "🔓 Verify & Sign In"
            )}
          </button>

          <div className={styles.mfaHelpText}>
            <p>Open your authenticator app (Google Authenticator, Authy, etc.) and enter the current code.</p>
          </div>

          <button
            onClick={() => {
              setStep("login");
              setMfaCode(["", "", "", "", "", ""]);
              setError("");
              setMfaFactor(null);
            }}
            className={`btn btn-ghost ${styles.mfaBackBtn}`}
            id="mfa-back-btn"
          >
            ← Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  // ── Standard Login Step ────────────────────────────────────────
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
              <Link href="/reset-password" className={styles.forgotLink}>Forgot?</Link>
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

export default function LoginPage() {
  return (
    <Suspense fallback={<div className={styles.authPage}><div className="loader" /></div>}>
      <LoginForm />
    </Suspense>
  );
}
