"use client";

import { useState, useEffect } from "react";
import styles from "./settings.module.css";
import { settingsApi, analyticsApi, type UserSettings } from "@/lib/api";

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
  }, []);

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
