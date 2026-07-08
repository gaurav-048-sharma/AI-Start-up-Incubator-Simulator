"use client";

import { useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import styles from "./auth.module.css";

type Step = "details" | "otp";

function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get("next") || "/dashboard";

  const [step, setStep] = useState<Step>("details");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [otpCode, setOtpCode] = useState(["", "", "", "", "", ""]);
  const codeInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !fullName) return;
    
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Failed to sign up");
      }
      
      setStep("otp");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    const code = otpCode.join("");
    if (code.length !== 6) {
      setError("Please enter a complete 6-digit code");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/auth/verify-signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp: code }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Invalid OTP");
      }
      
      // Save JWT token
      localStorage.setItem("access_token", data.access_token);
      
      // Redirect
      window.location.href = nextUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
      setOtpCode(["", "", "", "", "", ""]);
      codeInputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleCodeChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const newCode = [...otpCode];
    newCode[index] = value.slice(-1);
    setOtpCode(newCode);
    if (value && index < 5) codeInputRefs.current[index + 1]?.focus();
    if (newCode.every((d) => d !== "") && newCode.join("").length === 6) {
      setTimeout(() => handleVerifyOtp(), 100);
    }
  };

  const handleCodeKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otpCode[index] && index > 0) {
      codeInputRefs.current[index - 1]?.focus();
    }
    if (e.key === "Enter") handleVerifyOtp();
  };

  const handleCodePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length > 0) {
      const newCode = [...otpCode];
      for (let i = 0; i < pasted.length; i++) newCode[i] = pasted[i];
      setOtpCode(newCode);
      if (pasted.length === 6) {
        setTimeout(() => handleVerifyOtp(), 100);
      } else {
        codeInputRefs.current[pasted.length]?.focus();
      }
    }
  };

  if (step === "otp") {
    return (
      <div className={styles.authPage}>
        <div className={styles.orbTop} />
        <div className={styles.orbBottom} />
        <div className={`${styles.authCard} glass-card animate-fade-in`}>
          <div className={styles.logoContainer}>
            <div className={styles.logo}>🛡️</div>
            <div className={styles.logoGlow} />
          </div>
          <h1 className={styles.title}>Verify Email</h1>
          <p className={styles.subtitle}>We sent a 6-digit code to {email}</p>

          {error && <div className={styles.errorBanner}>⚠️ {error}</div>}

          <div className={styles.mfaCodeContainer}>
            {otpCode.map((digit, i) => (
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
                disabled={loading}
              />
            ))}
          </div>

          <button onClick={handleVerifyOtp} className="btn btn-primary btn-lg" style={{ width: "100%", marginTop: "var(--space-4)" }} disabled={loading || otpCode.join("").length !== 6}>
            {loading ? <><span className="loader" /> Verifying...</> : "Verify & Sign In"}
          </button>
          
          <button onClick={() => setStep("details")} className={`btn btn-ghost ${styles.mfaBackBtn}`}>
            ← Back
          </button>
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
        <p className={styles.subtitle}>Sign up for AI Incubator</p>

        {error && <div className={styles.errorBanner}>⚠️ {error}</div>}

        <form onSubmit={handleSignup} className={styles.form}>
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="signup-name">Full Name</label>
            <input
              id="signup-name"
              className="input"
              type="text"
              placeholder="John Doe"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              autoFocus
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
            />
          </div>
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="signup-password">Password</label>
            <input
              id="signup-password"
              className="input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>
          <button type="submit" className="btn btn-primary btn-lg" style={{ width: "100%" }} disabled={loading}>
            {loading ? <><span className="loader" /> Creating...</> : "Sign Up"}
          </button>
          
          <div style={{ marginTop: "1rem", textAlign: "center", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
            Already have an account? <Link href="/login" style={{ color: "var(--primary)" }}>Log in</Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className={styles.authPage}><div className="loader" /></div>}>
      <SignupForm />
    </Suspense>
  );
}
