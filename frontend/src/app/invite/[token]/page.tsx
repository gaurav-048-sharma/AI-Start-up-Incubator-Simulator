"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import styles from "./invite.module.css";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

export default function InviteAcceptPage() {
  const router = useRouter();
  const params = useParams();
  const token = params.token as string;
  const { user } = useAuth();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [orgData, setOrgData] = useState<{ org_id: string; role: string } | null>(null);

  const handleAccept = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await apiRequest<{ success: boolean; organization_id: string; role: string }>(
        `/api/organizations/invitations/${token}/accept`,
        { method: "POST" }
      );
      
      setSuccess(true);
      setOrgData({ org_id: response.organization_id, role: response.role });
      
      // Redirect to dashboard after a short delay
      setTimeout(() => {
        router.push("/dashboard");
      }, 3000);
      
    } catch (err: any) {
      if (err.message.includes("401") || err.message.toLowerCase().includes("unauthorized")) {
        setError("You must be logged in to accept this invitation.");
      } else {
        setError(err.message || "Failed to accept invitation. It may be invalid or expired.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (success && orgData) {
    return (
      <div className={styles.invitePage}>
        <div className={styles.orbTop} />
        <div className={styles.orbBottom} />
        <div className={`${styles.card} animate-fade-in`}>
          <div className={styles.icon}>🎉</div>
          <h1 className={styles.title}>Welcome to the Team!</h1>
          <p className={styles.subtitle}>
            You have successfully joined as a <strong>{orgData.role.replace("_", " ").toUpperCase()}</strong>.
            <br/><br/>
            Redirecting you to your new secure workspace...
          </p>
          <div className="loader" style={{ margin: "0 auto" }} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.invitePage}>
      <div className={styles.orbTop} />
      <div className={styles.orbBottom} />

      <div className={`${styles.card} animate-fade-in`}>
        <div className={styles.icon}>✉️</div>
        <h1 className={styles.title}>You've Been Invited</h1>
        <p className={styles.subtitle}>
          You've been invited to join an Enterprise Workspace on AI Incubator Simulator.
        </p>

        {error && (
          <div className={styles.errorBanner}>
            ⚠️ {error}
          </div>
        )}

        <div className={styles.actionArea}>
          {!user ? (
            <div className={styles.authPrompt}>
              <p style={{ marginBottom: "1rem", color: "var(--color-gray-300)" }}>
                Please sign up or log in to accept this invitation.
              </p>
              <Link href={`/signup?next=/invite/${token}`} className="btn btn-primary btn-lg" style={{ display: "block", marginBottom: "0.5rem" }}>
                Create Account
              </Link>
              <Link href={`/login?next=/invite/${token}`} className="btn btn-outline btn-lg" style={{ display: "block" }}>
                Log In
              </Link>
            </div>
          ) : (
            <div>
              <p style={{ marginBottom: "1.5rem", color: "var(--color-gray-300)" }}>
                You are logged in as <strong>{user.email}</strong>.
              </p>
              <button 
                className="btn btn-primary btn-lg" 
                style={{ width: "100%" }}
                onClick={handleAccept}
                disabled={loading}
              >
                {loading ? <><span className="loader" /> Processing...</> : "Accept Invitation"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
