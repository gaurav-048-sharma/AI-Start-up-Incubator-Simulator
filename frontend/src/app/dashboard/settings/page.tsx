"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./settings.module.css";
import { settingsApi, analyticsApi, mfaApi, type UserSettings, type MfaFactor } from "@/lib/api";

type MfaSetupStep = "idle" | "enrolling" | "scan_qr" | "verify" | "success";

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>({
    user_id: "demo-user",
    llm_provider: "openai",
    llm_model: "gpt-4o",
    max_iterations: 5,
    quality_threshold: 0.7,
    notification_email: true,
    notification_in_app: true,
    webhook_url: "",
    theme: "dark",
  });
  const [credits, setCredits] = useState(10);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // MFA State
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [mfaFactors, setMfaFactors] = useState<MfaFactor[]>([]);
  const [mfaSetupStep, setMfaSetupStep] = useState<MfaSetupStep>("idle");
  const [mfaQrCode, setMfaQrCode] = useState("");
  const [mfaSecret, setMfaSecret] = useState("");
  const [mfaFactorId, setMfaFactorId] = useState("");
  const [mfaCode, setMfaCode] = useState(["", "", "", "", "", ""]);
  const [mfaError, setMfaError] = useState("");
  const [mfaLoading, setMfaLoading] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [disableCode, setDisableCode] = useState("");
  const [showDisableConfirm, setShowDisableConfirm] = useState(false);
  const codeInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const [settingsData, creditsData] = await Promise.allSettled([
          settingsApi.get(),
          analyticsApi.getCredits(),
        ]);
        if (settingsData.status === "fulfilled") {
          setSettings(settingsData.value);
        }
        if (creditsData.status === "fulfilled") {
          setCredits(creditsData.value.credits);
        }
      } catch {
        /* use defaults */
      } finally {
        setLoading(false);
      }
    }
    load();
    loadMfaStatus();
  }, []);

  const loadMfaStatus = async () => {
    try {
      // Use Supabase client directly for accurate MFA factor listing
      if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SUPABASE_URL) {
        const { createClient } = await import("@/lib/supabase/client");
        const supabase = createClient();
        if (supabase) {
          const { data } = await supabase.auth.mfa.listFactors();
          if (data?.totp) {
            const verified = data.totp.filter((f: { status: string }) => f.status === "verified");
            setMfaFactors(verified.map((f: { id: string; friendly_name?: string; factor_type: string; status: string; created_at: string; updated_at: string }) => ({
              id: f.id,
              friendly_name: f.friendly_name,
              factor_type: f.factor_type,
              status: f.status as "verified" | "unverified",
              created_at: f.created_at,
              updated_at: f.updated_at,
            })));
            setMfaEnabled(verified.length > 0);
          }
        }
      }

      // Also check if MFA is required for this user's role
      try {
        const status = await mfaApi.getStatus();
        setMfaRequired(status.mfa_required);
      } catch {
        // Backend may not be connected
      }
    } catch {
      // silent
    }
  };

  const handleStartEnrollment = async () => {
    setMfaSetupStep("enrolling");
    setMfaError("");
    setMfaLoading(true);

    try {
      if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SUPABASE_URL) {
        const { createClient } = await import("@/lib/supabase/client");
        const supabase = createClient();
        if (!supabase) throw new Error("Auth not configured");

        const { data, error } = await supabase.auth.mfa.enroll({
          factorType: "totp",
          friendlyName: "Authenticator App",
        });

        if (error) throw error;
        if (!data) throw new Error("No enrollment data returned");

        setMfaFactorId(data.id);
        setMfaQrCode(data.totp.qr_code);
        setMfaSecret(data.totp.secret);
        setMfaSetupStep("scan_qr");
      }
    } catch (err) {
      setMfaError(err instanceof Error ? err.message : "Failed to start enrollment");
      setMfaSetupStep("idle");
    } finally {
      setMfaLoading(false);
    }
  };

  const handleVerifyEnrollment = async () => {
    const code = mfaCode.join("");
    if (code.length !== 6) {
      setMfaError("Please enter a complete 6-digit code");
      return;
    }

    setMfaLoading(true);
    setMfaError("");

    try {
      if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SUPABASE_URL) {
        const { createClient } = await import("@/lib/supabase/client");
        const supabase = createClient();
        if (!supabase) throw new Error("Auth not configured");

        // Challenge the factor
        const { data: challengeData, error: challengeError } = await supabase.auth.mfa.challenge({
          factorId: mfaFactorId,
        });

        if (challengeError) throw challengeError;
        if (!challengeData) throw new Error("Challenge creation failed");

        // Verify with the TOTP code
        const { error: verifyError } = await supabase.auth.mfa.verify({
          factorId: mfaFactorId,
          challengeId: challengeData.id,
          code,
        });

        if (verifyError) {
          setMfaError("Invalid code. Please check your authenticator app and try again.");
          setMfaCode(["", "", "", "", "", ""]);
          codeInputRefs.current[0]?.focus();
          setMfaLoading(false);
          return;
        }

        // Success!
        setMfaSetupStep("success");
        setMfaEnabled(true);
        await loadMfaStatus();

        // Auto-dismiss success after 3s
        setTimeout(() => {
          setMfaSetupStep("idle");
          setMfaCode(["", "", "", "", "", ""]);
          setMfaQrCode("");
          setMfaSecret("");
        }, 3000);
      }
    } catch (err) {
      setMfaError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setMfaLoading(false);
    }
  };

  const handleDisableMfa = async () => {
    if (!mfaFactors.length) return;
    
    setMfaLoading(true);
    setMfaError("");

    try {
      if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SUPABASE_URL) {
        const { createClient } = await import("@/lib/supabase/client");
        const supabase = createClient();
        if (!supabase) throw new Error("Auth not configured");

        const { error } = await supabase.auth.mfa.unenroll({
          factorId: mfaFactors[0].id,
        });

        if (error) throw error;

        setMfaEnabled(false);
        setMfaFactors([]);
        setShowDisableConfirm(false);
        setDisableCode("");
        await loadMfaStatus();
      }
    } catch (err) {
      setMfaError(err instanceof Error ? err.message : "Failed to disable MFA");
    } finally {
      setMfaLoading(false);
    }
  };

  // Handle individual code digit input
  const handleCodeChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const newCode = [...mfaCode];
    newCode[index] = value.slice(-1);
    setMfaCode(newCode);
    if (value && index < 5) {
      codeInputRefs.current[index + 1]?.focus();
    }
  };

  const handleCodeKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !mfaCode[index] && index > 0) {
      codeInputRefs.current[index - 1]?.focus();
    }
    if (e.key === "Enter") {
      handleVerifyEnrollment();
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
      if (pasted.length < 6) {
        codeInputRefs.current[pasted.length]?.focus();
      }
    }
  };

  const handleUpgrade = async (tier: string) => {
    try {
      const resp = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("supabase_session") ? JSON.parse(localStorage.getItem("supabase_session")!).access_token : ""}`,
          "X-Org-Id": localStorage.getItem("activeOrgId") || "",
        },
        body: JSON.stringify({ tier })
      });
      if (!resp.ok) throw new Error("Checkout failed");
      const data = await resp.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch {
      alert("Failed to initiate checkout");
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const updated = await settingsApi.update({
        llm_provider: settings.llm_provider,
        llm_model: settings.llm_model,
        max_iterations: settings.max_iterations,
        quality_threshold: settings.quality_threshold,
        notification_email: settings.notification_email,
        notification_in_app: settings.notification_in_app,
        webhook_url: settings.webhook_url || undefined,
        theme: settings.theme,
      });
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const MODEL_OPTIONS: Record<string, { value: string; label: string }[]> = {
    openai: [
      { value: "gpt-4o", label: "GPT-4o" },
      { value: "gpt-4o-mini", label: "GPT-4o Mini" },
      { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
    ],
    anthropic: [
      { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
      { value: "claude-3-haiku-20240307", label: "Claude 3 Haiku" },
    ],
  };

  if (loading) {
    return (
      <div className={`${styles.wrapper} animate-fade-in`}>
        <div className={`${styles.section} glass-card`}>
          <div className="skeleton" style={{ height: 24, width: "40%", marginBottom: 16 }} />
          <div className="skeleton" style={{ height: 40, width: "100%", marginBottom: 12 }} />
          <div className="skeleton" style={{ height: 40, width: "100%" }} />
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.wrapper} animate-fade-in`}>
      {/* Credits Banner */}
      <div className={`${styles.creditsBanner} glass-card`}>
        <div className={styles.creditsInfo}>
          <span className={styles.creditsIcon}>🪙</span>
          <div>
            <div className={styles.creditsValue}>{credits}</div>
            <div className={styles.creditsLabel}>Credits Remaining</div>
          </div>
        </div>
        <div className={styles.creditsActions}>
          <span className={`badge ${credits > 5 ? "badge-success" : credits > 2 ? "badge-warning" : "badge-error"}`}>
            {credits > 5 ? "Healthy" : credits > 2 ? "Low" : "Critical"}
          </span>
        </div>
      </div>

      {/* ══ Two-Factor Authentication ══════════════════════════════ */}
      <div className={`${styles.section} glass-card`} id="mfa-section">
        <div className={styles.mfaSectionHeader}>
          <div>
            <h3 className={styles.sectionTitle}>🔐 Two-Factor Authentication</h3>
            <p className={styles.sectionDesc}>
              Add an extra layer of security to your account using an authenticator app.
            </p>
          </div>
          {mfaEnabled && (
            <span className={styles.mfaActiveBadge}>
              <span className={styles.mfaActiveDot} />
              2FA Active
            </span>
          )}
        </div>

        {mfaRequired && !mfaEnabled && (
          <div className={styles.mfaRequiredBanner}>
            <span>⚠️</span>
            <div>
              <strong>MFA Required</strong>
              <p>Your role requires two-factor authentication. Enable it below to continue using admin features.</p>
            </div>
          </div>
        )}

        {mfaError && (
          <div className={styles.mfaErrorBanner}>
            <span>⚠️</span> {mfaError}
          </div>
        )}

        {/* ── Idle: Show enable/disable ────────────────────────── */}
        {mfaSetupStep === "idle" && !mfaEnabled && (
          <div className={styles.mfaEnableCard}>
            <div className={styles.mfaEnableIcon}>🛡️</div>
            <div className={styles.mfaEnableContent}>
              <h4>Protect your account</h4>
              <p>Use an authenticator app like Google Authenticator, Authy, or 1Password to generate verification codes.</p>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleStartEnrollment}
              disabled={mfaLoading}
              id="enable-mfa-btn"
            >
              {mfaLoading ? <><span className="loader" /> Setting up...</> : "Enable 2FA"}
            </button>
          </div>
        )}

        {mfaSetupStep === "idle" && mfaEnabled && (
          <div className={styles.mfaStatusCard}>
            <div className={styles.mfaStatusInfo}>
              <div className={styles.mfaStatusIcon}>✅</div>
              <div>
                <h4>Two-factor authentication is enabled</h4>
                <p>Your account is protected with TOTP verification.</p>
                {mfaFactors[0] && (
                  <span className={styles.mfaFactorMeta}>
                    Factor: {mfaFactors[0].friendly_name || "Authenticator App"} · Added {new Date(mfaFactors[0].created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
            {!mfaRequired ? (
              <div>
                {!showDisableConfirm ? (
                  <button
                    className="btn btn-outline"
                    onClick={() => setShowDisableConfirm(true)}
                    style={{ borderColor: "var(--error)", color: "var(--error)" }}
                    id="disable-mfa-btn"
                  >
                    Disable 2FA
                  </button>
                ) : (
                  <div className={styles.mfaDisableConfirm}>
                    <p>Are you sure? This reduces account security.</p>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        className="btn btn-sm"
                        onClick={() => setShowDisableConfirm(false)}
                      >
                        Cancel
                      </button>
                      <button
                        className="btn btn-sm"
                        style={{ background: "var(--error)", color: "white" }}
                        onClick={handleDisableMfa}
                        disabled={mfaLoading}
                      >
                        {mfaLoading ? "Removing..." : "Confirm Disable"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <span className={styles.mfaMandatoryBadge}>Mandatory for your role</span>
            )}
          </div>
        )}

        {/* ── Enrolling spinner ────────────────────────────────── */}
        {mfaSetupStep === "enrolling" && (
          <div className={styles.mfaEnrollLoading}>
            <span className="loader" style={{ width: 32, height: 32 }} />
            <p>Generating your secure key...</p>
          </div>
        )}

        {/* ── Scan QR Code Step ────────────────────────────────── */}
        {mfaSetupStep === "scan_qr" && (
          <div className={styles.mfaSetupWizard}>
            <div className={styles.mfaStepIndicator}>
              <div className={`${styles.mfaStep} ${styles.mfaStepActive}`}>
                <span>1</span> Scan QR Code
              </div>
              <div className={styles.mfaStepDivider} />
              <div className={styles.mfaStep}>
                <span>2</span> Enter Code
              </div>
              <div className={styles.mfaStepDivider} />
              <div className={styles.mfaStep}>
                <span>3</span> Verified
              </div>
            </div>

            <div className={styles.mfaQrContainer}>
              {mfaQrCode && (
                <div className={styles.mfaQrWrapper}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={mfaQrCode}
                    alt="Scan this QR code with your authenticator app"
                    className={styles.mfaQrImage}
                    width={200}
                    height={200}
                  />
                </div>
              )}
              <div className={styles.mfaQrInstructions}>
                <h4>Scan with your authenticator app</h4>
                <ol>
                  <li>Open Google Authenticator, Authy, or 1Password</li>
                  <li>Tap the &quot;+&quot; button to add a new account</li>
                  <li>Scan this QR code</li>
                </ol>

                <div className={styles.mfaSecretToggle}>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => setShowSecret(!showSecret)}
                  >
                    {showSecret ? "Hide" : "Show"} manual key
                  </button>
                  {showSecret && (
                    <div className={styles.mfaSecretDisplay}>
                      <code>{mfaSecret}</code>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => {
                          navigator.clipboard.writeText(mfaSecret);
                        }}
                        title="Copy to clipboard"
                      >
                        📋
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <button
              className="btn btn-primary"
              onClick={() => {
                setMfaSetupStep("verify");
                setTimeout(() => codeInputRefs.current[0]?.focus(), 100);
              }}
              style={{ width: "100%", marginTop: "var(--space-4)" }}
            >
              I&apos;ve scanned the code →
            </button>

            <button
              className="btn btn-ghost"
              onClick={() => {
                setMfaSetupStep("idle");
                setMfaQrCode("");
                setMfaSecret("");
              }}
              style={{ width: "100%", marginTop: "var(--space-2)" }}
            >
              Cancel
            </button>
          </div>
        )}

        {/* ── Verify Code Step ─────────────────────────────────── */}
        {mfaSetupStep === "verify" && (
          <div className={styles.mfaSetupWizard}>
            <div className={styles.mfaStepIndicator}>
              <div className={`${styles.mfaStep} ${styles.mfaStepDone}`}>
                <span>✓</span> Scan QR Code
              </div>
              <div className={`${styles.mfaStepDivider} ${styles.mfaStepDividerDone}`} />
              <div className={`${styles.mfaStep} ${styles.mfaStepActive}`}>
                <span>2</span> Enter Code
              </div>
              <div className={styles.mfaStepDivider} />
              <div className={styles.mfaStep}>
                <span>3</span> Verified
              </div>
            </div>

            <p className={styles.mfaVerifyDesc}>
              Enter the 6-digit code shown in your authenticator app to confirm setup.
            </p>

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
                  id={`settings-mfa-code-${i}`}
                />
              ))}
            </div>

            <button
              className="btn btn-primary"
              onClick={handleVerifyEnrollment}
              disabled={mfaLoading || mfaCode.join("").length !== 6}
              style={{ width: "100%", marginTop: "var(--space-4)" }}
              id="verify-mfa-setup-btn"
            >
              {mfaLoading ? <><span className="loader" /> Verifying...</> : "Verify & Enable 2FA"}
            </button>

            <button
              className="btn btn-ghost"
              onClick={() => setMfaSetupStep("scan_qr")}
              style={{ width: "100%", marginTop: "var(--space-2)" }}
            >
              ← Back to QR Code
            </button>
          </div>
        )}

        {/* ── Success Step ─────────────────────────────────────── */}
        {mfaSetupStep === "success" && (
          <div className={styles.mfaSetupWizard}>
            <div className={styles.mfaStepIndicator}>
              <div className={`${styles.mfaStep} ${styles.mfaStepDone}`}>
                <span>✓</span> Scan QR Code
              </div>
              <div className={`${styles.mfaStepDivider} ${styles.mfaStepDividerDone}`} />
              <div className={`${styles.mfaStep} ${styles.mfaStepDone}`}>
                <span>✓</span> Enter Code
              </div>
              <div className={`${styles.mfaStepDivider} ${styles.mfaStepDividerDone}`} />
              <div className={`${styles.mfaStep} ${styles.mfaStepActive} ${styles.mfaStepDone}`}>
                <span>✓</span> Verified
              </div>
            </div>

            <div className={styles.mfaSuccessCard}>
              <div className={styles.mfaSuccessIcon}>🎉</div>
              <h4>Two-Factor Authentication Enabled!</h4>
              <p>Your account is now protected with TOTP verification. You&apos;ll be asked for a code each time you sign in.</p>
            </div>
          </div>
        )}
      </div>

      {/* Subscription & Billing */}
      <div className={`${styles.section} glass-card`}>
        <h3 className={styles.sectionTitle}>💰 Subscription & Billing</h3>
        <p className={styles.sectionDesc}>Upgrade your plan or request Enterprise access.</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div className="glass-card" style={{ padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: 8 }}>
            <h4 style={{ margin: 0 }}>Pro Plan</h4>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--fs-sm)" }}>Unlock unlimited ideas and full 5-agent workflows.</p>
            <div style={{ marginTop: "auto", paddingTop: 16 }}>
              <button className="btn btn-primary" onClick={() => handleUpgrade("pro")} style={{ width: "100%" }}>Upgrade to Pro</button>
            </div>
          </div>
          <div className="glass-card" style={{ padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: 8 }}>
            <h4 style={{ margin: 0 }}>Enterprise Access</h4>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--fs-sm)" }}>For large teams. Includes team collaboration and SSO.</p>
            <div style={{ marginTop: "auto", paddingTop: 16 }}>
              <button className="btn btn-outline" onClick={() => window.location.href = "/enterprise"} style={{ width: "100%" }}>Request Access</button>
            </div>
          </div>
        </div>
      </div>

      {/* LLM Configuration */}
      <div className={`${styles.section} glass-card`}>
        <h3 className={styles.sectionTitle}>🤖 LLM Configuration</h3>
        <p className={styles.sectionDesc}>Choose your AI model provider and settings.</p>
        <div className={styles.fieldRow}>
          <div className={styles.fieldGroup}>
            <label className="input-label">Provider</label>
            <select
              className="input"
              value={settings.llm_provider}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  llm_provider: e.target.value,
                  llm_model: MODEL_OPTIONS[e.target.value]?.[0]?.value || "gpt-4o",
                })
              }
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>
          <div className={styles.fieldGroup}>
            <label className="input-label">Model</label>
            <select
              className="input"
              value={settings.llm_model}
              onChange={(e) => setSettings({ ...settings, llm_model: e.target.value })}
            >
              {(MODEL_OPTIONS[settings.llm_provider] || []).map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Workflow Settings */}
      <div className={`${styles.section} glass-card`}>
        <h3 className={styles.sectionTitle}>⚙️ Workflow Settings</h3>
        <div className={styles.fieldRow}>
          <div className={styles.fieldGroup}>
            <label className="input-label">Max Iterations</label>
            <input
              className="input"
              type="number"
              min={1}
              max={15}
              value={settings.max_iterations}
              onChange={(e) => setSettings({ ...settings, max_iterations: Number(e.target.value) })}
            />
          </div>
          <div className={styles.fieldGroup}>
            <label className="input-label">Quality Threshold</label>
            <input
              className="input"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={settings.quality_threshold}
              onChange={(e) => setSettings({ ...settings, quality_threshold: Number(e.target.value) })}
            />
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className={`${styles.section} glass-card`}>
        <h3 className={styles.sectionTitle}>🔔 Notifications</h3>
        <p className={styles.sectionDesc}>Control how you receive updates about your workflows.</p>
        <div className={styles.toggleGroup}>
          <label className={styles.toggleRow}>
            <span>In-app notifications</span>
            <input
              type="checkbox"
              checked={settings.notification_in_app}
              onChange={(e) => setSettings({ ...settings, notification_in_app: e.target.checked })}
            />
          </label>
          <label className={styles.toggleRow}>
            <span>Email notifications</span>
            <input
              type="checkbox"
              checked={settings.notification_email}
              onChange={(e) => setSettings({ ...settings, notification_email: e.target.checked })}
            />
          </label>
        </div>
        <div className={styles.fieldGroup} style={{ marginTop: "var(--space-4)" }}>
          <label className="input-label">Webhook URL (optional)</label>
          <input
            className="input"
            type="url"
            placeholder="https://hooks.slack.com/services/..."
            value={settings.webhook_url || ""}
            onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
          />
          <span style={{ fontSize: "var(--fs-xs)", color: "var(--text-muted)", marginTop: 4 }}>
            Receive POST requests when workflows or simulations complete.
          </span>
        </div>
      </div>

      {/* Save */}
      <div className={styles.saveRow}>
        {error && (
          <div style={{ color: "var(--error)", fontSize: "var(--fs-sm)" }}>{error}</div>
        )}
        {saved && (
          <div style={{ color: "var(--success)", fontSize: "var(--fs-sm)", display: "flex", alignItems: "center", gap: 6 }}>
            ✅ Settings saved successfully
          </div>
        )}
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
          id="save-settings-btn"
        >
          {saving ? (<><span className="loader" /> Saving...</>) : "💾 Save Settings"}
        </button>
      </div>
    </div>
  );
}
