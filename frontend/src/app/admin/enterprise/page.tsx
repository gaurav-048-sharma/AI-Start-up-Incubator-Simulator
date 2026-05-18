"use client";

import { useEffect, useState } from "react";
import styles from "./admin.module.css";
import { apiRequest } from "@/lib/api";

interface EnterpriseRequest {
  id: string;
  company_name: string;
  contact_name: string;
  contact_email: string;
  team_size: string;
  industry: string;
  required_seats: number;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

export default function EnterpriseAdminDashboard() {
  const [requests, setRequests] = useState<EnterpriseRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchRequests = async () => {
    try {
      const data = await apiRequest<{ requests: EnterpriseRequest[] }>("/api/enterprise/requests");
      setRequests(data.requests);
    } catch (err: any) {
      setError(err.message || "Failed to load enterprise requests.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleApprove = async (id: string) => {
    if (!confirm("Are you sure you want to approve this request and provision a new enterprise organization?")) return;
    
    setProcessingId(id);
    try {
      await apiRequest(`/api/enterprise/approve/${id}`, { method: "POST" });
      alert("Enterprise provisioned successfully! An invitation email has been sent.");
      fetchRequests(); // Refresh list
    } catch (err: any) {
      alert("Error: " + err.message);
    } finally {
      setProcessingId(null);
    }
  };

  if (loading) {
    return <div className={styles.adminPage}><div className="loader" style={{margin:"0 auto"}} /></div>;
  }

  return (
    <div className={styles.adminPage}>
      <div className={styles.header}>
        <h1 className={styles.title}>Enterprise Access Requests</h1>
      </div>

      {error && (
        <div style={{ color: "#ef4444", marginBottom: "1rem", padding: "1rem", background: "rgba(239, 68, 68, 0.1)", borderRadius: "8px" }}>
          ⚠️ {error}
        </div>
      )}

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Company</th>
              <th>Contact</th>
              <th>Details</th>
              <th>Status</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {requests.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className={styles.emptyState}>No enterprise requests found.</div>
                </td>
              </tr>
            ) : (
              requests.map((req) => (
                <tr key={req.id}>
                  <td>
                    <strong>{req.company_name}</strong>
                  </td>
                  <td>
                    <div>{req.contact_name}</div>
                    <div style={{ fontSize: "0.8rem", color: "var(--color-gray-400)" }}>{req.contact_email}</div>
                  </td>
                  <td>
                    <div style={{ fontSize: "0.85rem" }}>
                      Seats: {req.required_seats || "N/A"}<br/>
                      Size: {req.team_size || "N/A"}<br/>
                      Industry: {req.industry || "N/A"}
                    </div>
                  </td>
                  <td>
                    <span className={`${styles.statusBadge} ${styles[`status_${req.status}`]}`}>
                      {req.status}
                    </span>
                  </td>
                  <td>
                    {new Date(req.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    {req.status === "pending" && (
                      <div className={styles.actions}>
                        <button 
                          className={styles.btnApprove} 
                          onClick={() => handleApprove(req.id)}
                          disabled={processingId === req.id}
                        >
                          {processingId === req.id ? "Approving..." : "Approve"}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
