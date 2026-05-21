"use client";

import { useCallback, useEffect, useState } from "react";
import styles from "./admin.module.css";
import { adminApi, authApi } from "@/lib/api";
import type { EnterpriseRequest as EnterpriseReqType, Organization, PlatformUser } from "@/lib/api";

type EnterpriseRequest = EnterpriseReqType;
type AdminOrg = Organization & { status?: string; subscription_status?: string };

export default function EnterpriseAdminDashboard() {
  const [activeTab, setActiveTab] = useState<"requests" | "organizations" | "users">("requests");
  const [requests, setRequests] = useState<EnterpriseRequest[]>([]);
  const [organizations, setOrganizations] = useState<AdminOrg[]>([]);
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isUnauthorized, setIsUnauthorized] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const getErrorMessage = (err: unknown, fallback: string) =>
    err instanceof Error ? err.message : fallback;

  const fetchRequests = useCallback(async () => {
    try {
      const data = await adminApi.listEnterpriseRequests();
      setRequests(data.requests);
    } catch (err: unknown) {
      const message = getErrorMessage(err, "Failed to load enterprise requests.");
      if (message.includes("platform_role") || message.includes("Platform role") || message.includes("401")) {
        setIsUnauthorized(true);
      } else {
        setError(message);
      }
    }
  }, []);

  const fetchOrganizations = useCallback(async () => {
    try {
      const data = await adminApi.listAllOrganizations();
      setOrganizations(data.organizations as AdminOrg[]);
    } catch (err: unknown) {
      const message = getErrorMessage(err, "Failed to load organizations.");
      if (message.includes("platform_role") || message.includes("Platform role") || message.includes("401")) {
        setIsUnauthorized(true);
      } else {
        setError(message);
      }
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      const data = await adminApi.listUsers();
      setUsers(data.users);
    } catch (err: unknown) {
      const message = getErrorMessage(err, "Failed to load users.");
      if (message.includes("platform_role") || message.includes("Platform role") || message.includes("401")) {
        setIsUnauthorized(true);
      } else {
        setError(message);
      }
    }
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchRequests(), fetchOrganizations(), fetchUsers()]);
    setLoading(false);
  }, [fetchRequests, fetchOrganizations, fetchUsers]);

  useEffect(() => {
    let mounted = true;

    authApi.me()
      .then((me) => {
        if (!mounted) return;
        if (me.platform_role !== "super_admin") {
          setIsUnauthorized(true);
          setLoading(false);
          return;
        }
        void loadData();
      })
      .catch(() => {
        if (!mounted) return;
        setIsUnauthorized(true);
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [loadData]);

  const handleApprove = async (id: string) => {
    if (!confirm("Are you sure you want to approve this request and generate a payment link?")) return;
    
    setProcessingId(id);
    try {
      const resp = await adminApi.approveEnterpriseRequest(id);
      alert("Enterprise request approved! Payment link sent.");
      if (resp.checkout_url) {
        // Optionally redirect or show the link to the admin
        if (confirm(`Payment link generated:\n\n${resp.checkout_url}\n\nOpen link now?`)) {
          window.open(resp.checkout_url, '_blank');
        }
      }
      loadData(); // Refresh list
    } catch (err: unknown) {
      alert("Error: " + getErrorMessage(err, "Failed to approve request."));
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (id: string) => {
    if (!confirm("Are you sure you want to reject this request?")) return;
    
    setProcessingId(id);
    try {
      await adminApi.rejectEnterpriseRequest(id);
      alert("Enterprise request rejected.");
      loadData();
    } catch (err: unknown) {
      alert("Error: " + getErrorMessage(err, "Failed to reject request."));
    } finally {
      setProcessingId(null);
    }
  };

  const handleToggleStatus = async (id: string, currentStatus: string) => {
    const newStatus = (currentStatus === "active" ? "suspended" : "active") as "active" | "suspended";
    if (!confirm(`Are you sure you want to ${newStatus === "suspended" ? "suspend" : "reactivate"} this organization?`)) return;
    
    try {
      await adminApi.updateOrgStatus(id, newStatus);
      fetchOrganizations();
    } catch (err: unknown) {
      alert("Error: " + getErrorMessage(err, "Failed to update status."));
    }
  };

  const handleDeleteOrg = async (id: string) => {
    if (!confirm("CRITICAL: Are you sure you want to delete this organization? This is irreversible!")) return;
    
    try {
      await adminApi.deleteOrganization(id);
      fetchOrganizations();
    } catch (err: unknown) {
      alert("Error: " + getErrorMessage(err, "Failed to delete organization."));
    }
  };

  const handleRoleUpdate = async (userId: string, newRole: string) => {
    if (!confirm(`Are you sure you want to update this user's platform role to ${newRole}?`)) return;
    try {
      await adminApi.updatePlatformRole(userId, newRole);
      fetchUsers();
    } catch (err: unknown) {
      alert("Error: " + getErrorMessage(err, "Failed to update role."));
    }
  };

  if (loading) {
    return <div className={styles.adminPage}><div className={`${styles.loadingWrap} loader`} /></div>;
  }

  if (isUnauthorized) {
    return (
      <div className={`${styles.adminPage} ${styles.accessDeniedWrap}`}>
        <h1 className={styles.accessDeniedCode}>403</h1>
        <h2 className={styles.accessDeniedTitle}>Access Denied</h2>
        <p className={styles.accessDeniedText}>
          You do not have the required <strong>Platform Super Admin</strong> role to view this page. Contact the platform administrator if you believe this is a mistake.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.adminPage}>
      <div className={styles.header}>
        <h1 className={styles.title}>Platform Admin Control Panel</h1>
      </div>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{requests.length}</div>
          <div className={styles.statLabel}>Pending Requests</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{organizations.length}</div>
          <div className={styles.statLabel}>Active Organizations</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{users.length}</div>
          <div className={styles.statLabel}>Total Users</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>1.2k</div>
          <div className={styles.statLabel}>Global Credits</div>
        </div>
      </div>

      <div className={styles.tabRow}>
        <button 
          className={`btn ${activeTab === "requests" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setActiveTab("requests")}
        >
          Approval Queue
        </button>
        <button 
          className={`btn ${activeTab === "organizations" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setActiveTab("organizations")}
        >
          Company Directory
        </button>
        <button 
          className={`btn ${activeTab === "users" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setActiveTab("users")}
        >
          Users
        </button>
      </div>

      {error && (
        <div className={styles.errorBox}>
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
                      <div className={styles.smallMuted}>{req.contact_email}</div>
                    </td>
                    <td>
                      <div className={styles.smallText}>
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
                      {req.status === "pending" ? (
                        <div className={styles.actions}>
                          <button 
                            className={styles.btnApprove} 
                            onClick={() => handleApprove(req.id)}
                            disabled={processingId === req.id}
                          >
                            {processingId === req.id ? "Approving..." : "Approve"}
                          </button>
                          <button 
                            className="btn btn-outline btn-sm"
                            onClick={() => handleReject(req.id)}
                            disabled={processingId === req.id}
                          >
                            Reject
                          </button>
                        </div>
                      ) : (
                        <span className={styles.smallMuted}>
                          Processed
                        </span>
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
                      <span className={`${styles.statusBadge} ${styles.planBadgeAlt}`}>
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
                          onClick={() => handleToggleStatus(org.id, org.status ?? "active")}
                        >
                          {org.status === 'active' ? 'Suspend' : 'Reactivate'}
                        </button>
                        <button className={`btn btn-outline btn-sm ${styles.deleteButton}`} onClick={() => handleDeleteOrg(org.id)}>
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

      {activeTab === "users" && (
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Platform Role</th>
                <th>Tier</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div className={styles.emptyState}>No users found.</div>
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <strong>{u.full_name || "Unknown"}</strong>
                    </td>
                    <td>{u.role}</td>
                    <td>
                      <span className={`${styles.statusBadge} ${u.platform_role === 'super_admin' ? styles.status_approved : ''}`}>
                        {u.platform_role}
                      </span>
                    </td>
                    <td>{u.tier}</td>
                    <td>
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <select 
                        value={u.platform_role}
                        onChange={(e) => handleRoleUpdate(u.id, e.target.value)}
                        className="select select-sm"
                        style={{ padding: '0.25rem' }}
                      >
                        <option value="user">User</option>
                        <option value="support">Support</option>
                        <option value="billing_admin">Billing Admin</option>
                        <option value="super_admin">Super Admin</option>
                      </select>
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
