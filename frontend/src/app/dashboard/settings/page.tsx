"use client";

import { useState } from "react";
import styles from "./settings.module.css";

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    openaiKey: "", anthropicKey: "", tavilyKey: "",
    llmProvider: "openai", model: "gpt-4o",
    maxIterations: 5, qualityThreshold: 0.7,
  });

  return (
    <div className={`${styles.wrapper} animate-fade-in`}>
      <div className={`${styles.section} glass-card`}>
        <h3 className={styles.sectionTitle}>🔑 API Keys</h3>
        <p className={styles.sectionDesc}>Configure your LLM and tool API keys.</p>
        <div className={styles.fieldGroup}>
          <label className="input-label">OpenAI API Key</label>
          <input className="input" type="password" placeholder="sk-..." value={settings.openaiKey}
            onChange={(e) => setSettings({ ...settings, openaiKey: e.target.value })} />
        </div>
        <div className={styles.fieldGroup}>
          <label className="input-label">Anthropic API Key</label>
          <input className="input" type="password" placeholder="sk-ant-..." value={settings.anthropicKey}
            onChange={(e) => setSettings({ ...settings, anthropicKey: e.target.value })} />
        </div>
        <div className={styles.fieldGroup}>
          <label className="input-label">Tavily API Key (Search)</label>
          <input className="input" type="password" placeholder="tvly-..." value={settings.tavilyKey}
            onChange={(e) => setSettings({ ...settings, tavilyKey: e.target.value })} />
        </div>
      </div>

      <div className={`${styles.section} glass-card`}>
        <h3 className={styles.sectionTitle}>🤖 LLM Configuration</h3>
        <div className={styles.fieldRow}>
          <div className={styles.fieldGroup}>
            <label className="input-label">Provider</label>
            <select className="input" value={settings.llmProvider}
              onChange={(e) => setSettings({ ...settings, llmProvider: e.target.value })}>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>
          <div className={styles.fieldGroup}>
            <label className="input-label">Model</label>
            <select className="input" value={settings.model}
              onChange={(e) => setSettings({ ...settings, model: e.target.value })}>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-4o-mini">GPT-4o Mini</option>
              <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
            </select>
          </div>
        </div>
      </div>

      <div className={`${styles.section} glass-card`}>
        <h3 className={styles.sectionTitle}>⚙️ Workflow Settings</h3>
        <div className={styles.fieldRow}>
          <div className={styles.fieldGroup}>
            <label className="input-label">Max Iterations</label>
            <input className="input" type="number" min={1} max={10} value={settings.maxIterations}
              onChange={(e) => setSettings({ ...settings, maxIterations: Number(e.target.value) })} />
          </div>
          <div className={styles.fieldGroup}>
            <label className="input-label">Quality Threshold</label>
            <input className="input" type="number" min={0} max={1} step={0.1} value={settings.qualityThreshold}
              onChange={(e) => setSettings({ ...settings, qualityThreshold: Number(e.target.value) })} />
          </div>
        </div>
      </div>

      <button className="btn btn-primary" id="save-settings-btn">💾 Save Settings</button>
    </div>
  );
}
