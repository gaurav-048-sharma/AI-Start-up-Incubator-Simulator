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
interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  max_members: number;
  status: string;
  created_at: string;
}

export default function EnterpriseAdminDashboard() {
  const [activeTab, setActiveTab] = useState<"requests" | "organizations">("requests");
  const [requests, setRequests] = useState<EnterpriseRequest[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isUnauthorized, setIsUnauthorized] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchRequests = async () => {
    try {
      const data = await apiRequest<{ requests: EnterpriseRequest[] }>("/api/enterprise/requests");
      setRequests(data.requests);
    } catch (err: any) {
      if (err.message?.includes("super_admin") || err.message?.includes("unauthorized")) {
        setIsUnauthorized(true);
      } else {
        setError(err.message || "Failed to load enterprise requests.");
      }
    }
  };

  const fetchOrganizations = async () => {
    try {
      const data = await apiRequest<{ organizations: Organization[] }>("/api/enterprise/organizations");
      setOrganizations(data.organizations);
    } catch (err: any) {
      if (err.message?.includes("super_admin") || err.message?.includes("unauthorized")) {
        setIsUnauthorized(true);
      } else {
        setError(err.message || "Failed to load organizations.");
      }
    }
  };

  const loadData = async () => {
    setLoading(true);
    await Promise.all([fetchRequests(), fetchOrganizations()]);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = async (id: string) => {
    if (!confirm("Are you sure you want to approve this request and provision a new enterprise organization?")) return;
    
    setProcessingId(id);
    try {
      await apiRequest(`/api/enterprise/approve/${id}`, { method: "POST" });
      alert("Enterprise provisioned successfully! An invitation email has been sent.");
      loadData(); // Refresh list
    } catch (err: any) {
      alert("Error: " + err.message);
    } finally {
      setProcessingId(null);
    }
  };

  const handleToggleStatus = async (id: string, currentStatus: string) => {
    const newStatus = currentStatus === "active" ? "suspended" : "active";
    if (!confirm(`Are you sure you want to ${newStatus === "suspended" ? "suspend" : "reactivate"} this organization?`)) return;
    
    try {
      await apiRequest(`/api/enterprise/organizations/${id}/status`, { 
        method: "PATCH",
        body: JSON.stringify({ status: newStatus })
      });
      fetchOrganizations();
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const handleDeleteOrg = async (id: string) => {
    if (!confirm("CRITICAL: Are you sure you want to delete this organization? This is irreversible!")) return;
    
    try {
      await apiRequest(`/api/enterprise/organizations/${id}`, { method: "DELETE" });
      fetchOrganizations(); // Refresh list
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  if (loading) {
    return <div className={styles.adminPage}><div className="loader" style={{margin:"0 auto"}} /></div>;
  }

  if (isUnauthorized) {
    return (
      <div className={styles.adminPage} style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "60vh", textAlign: "center" }}>
        <h1 style={{ fontSize: "4rem", marginBottom: "1rem", color: "#ef4444" }}>403</h1>
        <h2 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>Access Denied</h2>
        <p style={{ color: "var(--color-gray-400)", maxWidth: "400px" }}>
          You do not have the required <strong>super_admin</strong> permissions to view this page. If you believe this is a mistake, please contact the platform administrator.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.adminPage}>
      <div className={styles.header}>
        <h1 className={styles.title}>Super Admin Control Panel</h1>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem" }}>
        <button 
          className={`btn ${activeTab === "requests" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setActiveTab("requests")}
        >
          Pending Requests
        </button>
        <button 
          className={`btn ${activeTab === "organizations" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setActiveTab("organizations")}
        >
          Active Organizations
        </button>
      </div>

      {error && (
        <div style={{ color: "#ef4444", marginBottom: "1rem", padding: "1rem", background: "rgba(239, 68, 68, 0.1)", borderRadius: "8px" }}>
          ⚠️ {error}
        </div>
      )}

      {activeTab === "requests" && (
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
      )}

      {activeTab === "organizations" && (
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Organization Name</th>
                <th>URL Slug</th>
                <th>Plan</th>
                <th>Status</th>
                <th>Seat Limit</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {organizations.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div className={styles.emptyState}>No organizations found.</div>
                  </td>
                </tr>
              ) : (
                organizations.map((org) => (
                  <tr key={org.id}>
                    <td>
                      <strong>{org.name}</strong>
                    </td>
                    <td>{org.slug}</td>
                    <td>
                      <span className={styles.statusBadge} style={{ background: "rgba(168,85,247,0.2)", color: "#c084fc" }}>
                        {org.plan}
                      </span>
                    </td>
                    <td>
                      <span className={`${styles.statusBadge} ${org.status === 'active' ? styles.status_approved : styles.status_rejected}`}>
                        {org.status}
                      </span>
                    </td>
                    <td>{org.max_members} seats</td>
                    <td>
                      {new Date(org.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <div className={styles.actions}>
                        <button 
                          className="btn btn-outline btn-sm"
                          onClick={() => handleToggleStatus(org.id, org.status)}
                        >
                          {org.status === 'active' ? 'Suspend' : 'Reactivate'}
                        </button>
                        <button 
                          className="btn btn-outline btn-sm"
                          style={{ borderColor: "#ef4444", color: "#ef4444" }}
                          onClick={() => handleDeleteOrg(org.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
