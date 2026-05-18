"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "./enterprise.module.css";
import { apiRequest } from "@/lib/api";

export default function EnterpriseRequestPage() {
  const [formData, setFormData] = useState({
    company_name: "",
    contact_name: "",
    contact_email: "",
    team_size: "",
    industry: "",
    use_case: "",
    required_seats: "",
    compliance_requirements: "",
    billing_preferences: "",
    white_label_needs: false,
    notes: ""
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === "checkbox" ? (e.target as HTMLInputElement).checked : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const payload = {
        ...formData,
        required_seats: formData.required_seats ? parseInt(formData.required_seats, 10) : null
      };

      await apiRequest("/api/enterprise/request", {
        method: "POST",
        body: payload
      });
      
      setSuccess(true);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred while submitting your request.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className={styles.enterprisePage}>
        <div className={styles.orbTop} />
        <div className={styles.orbBottom} />
        <div className={`${styles.formCard} glass-card animate-fade-in`}>
          <div className={styles.successContent}>
            <div className={styles.successIcon}>🚀</div>
            <h1 className={styles.title}>Request Received</h1>
            <p className={styles.subtitle} style={{ marginBottom: "var(--space-6)" }}>
              Thank you for your interest, {formData.contact_name}. Our enterprise team will review your application and reach out to <strong>{formData.contact_email}</strong> shortly with next steps.
            </p>
            <Link href="/" className="btn btn-primary btn-lg">
              Return to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.enterprisePage}>
      <div className={styles.orbTop} />
      <div className={styles.orbBottom} />

      <div className={`${styles.formCard} glass-card animate-fade-in`}>
        <div className={styles.header}>
          <h1 className={styles.title}>Enterprise Access</h1>
          <p className={styles.subtitle}>
            Request dedicated infrastructure, multi-tenant organization management, and SSO for your incubator or venture studio.
          </p>
        </div>

        {error && (
          <div className={styles.errorBanner}>
            <span>⚠️</span> {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.formGrid}>
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="company_name">Company / Org Name *</label>
            <input
              id="company_name"
              name="company_name"
              className="input"
              placeholder="Acme Incubator"
              value={formData.company_name}
              onChange={handleChange}
              required
            />
          </div>

          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="contact_name">Your Name *</label>
            <input
              id="contact_name"
              name="contact_name"
              className="input"
              placeholder="Jane Doe"
              value={formData.contact_name}
              onChange={handleChange}
              required
            />
          </div>

          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="contact_email">Work Email *</label>
            <input
              id="contact_email"
              name="contact_email"
              className="input"
              type="email"
              placeholder="jane@acme.com"
              value={formData.contact_email}
              onChange={handleChange}
              required
            />
          </div>

          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="team_size">Team Size</label>
            <select
              id="team_size"
              name="team_size"
              className="input"
              value={formData.team_size}
              onChange={handleChange}
            >
              <option value="">Select size...</option>
              <option value="1-10">1-10</option>
              <option value="11-50">11-50</option>
              <option value="51-200">51-200</option>
              <option value="200+">200+</option>
            </select>
          </div>

          <div className={`${styles.fieldGroup} ${styles.fullWidth}`}>
            <label className="input-label" htmlFor="industry">Industry / Vertical</label>
            <input
              id="industry"
              name="industry"
              className="input"
              placeholder="e.g. University, FinTech Accelerator, Venture Studio"
              value={formData.industry}
              onChange={handleChange}
            />
          </div>

          <div className={`${styles.fieldGroup} ${styles.fullWidth}`}>
            <label className="input-label" htmlFor="use_case">Intended Use Case</label>
            <textarea
              id="use_case"
              name="use_case"
              className="input"
              placeholder="How do you plan to use the AI Incubator Simulator?"
              rows={3}
              value={formData.use_case}
              onChange={handleChange}
            />
          </div>
          
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="required_seats">Required Seats</label>
            <input
              id="required_seats"
              name="required_seats"
              className="input"
              type="number"
              min="1"
              placeholder="e.g. 50"
              value={formData.required_seats}
              onChange={handleChange}
            />
          </div>
          
          <div className={styles.fieldGroup}>
            <label className="input-label" htmlFor="billing_preferences">Billing Preference</label>
            <select
              id="billing_preferences"
              name="billing_preferences"
              className="input"
              value={formData.billing_preferences}
              onChange={handleChange}
            >
              <option value="">Select billing...</option>
              <option value="invoice">Manual Invoicing</option>
              <option value="credit_card">Credit Card (Stripe)</option>
              <option value="procurement">Enterprise Procurement</option>
            </select>
          </div>

          <div className={`${styles.fieldGroup} ${styles.fullWidth}`}>
            <label className="input-label" htmlFor="compliance_requirements">Compliance Requirements (Optional)</label>
            <input
              id="compliance_requirements"
              name="compliance_requirements"
              className="input"
              placeholder="e.g. SOC2, HIPAA, GDPR"
              value={formData.compliance_requirements}
              onChange={handleChange}
            />
          </div>

          <div className={`${styles.fieldGroup} ${styles.fullWidth}`}>
            <label className={styles.checkboxGroup}>
              <input
                type="checkbox"
                name="white_label_needs"
                checked={formData.white_label_needs}
                onChange={handleChange}
              />
              We need white-labeling / custom branding
            </label>
          </div>

          <div className={`${styles.fieldGroup} ${styles.fullWidth}`} style={{ marginTop: "var(--space-4)" }}>
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={loading}
              id="submit-enterprise-btn"
            >
              {loading ? (
                <><span className="loader" /> Submitting Request...</>
              ) : (
                "Request Enterprise Access"
              )}
            </button>
          </div>
        </form>

        <p className={styles.altLink}>
          Are you an individual founder?{" "}
          <Link href="/signup">Sign Up for Public SaaS</Link>
        </p>
      </div>
    </div>
  );
}
