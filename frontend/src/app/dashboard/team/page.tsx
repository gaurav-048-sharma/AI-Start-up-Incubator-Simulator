"use client";

import { useState, useEffect } from "react";
import styles from "./team.module.css";
import { organizationsApi, type Organization, type OrgMember, type RoleInfo } from "@/lib/api";

export default function TeamPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showInvite, setShowInvite] = useState(false);

  // Create org form
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");

  // Invite form
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("team_member");
  const [inviteLink, setInviteLink] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [orgsData, rolesData] = await Promise.all([
          organizationsApi.list(),
          organizationsApi.getRoles(),
        ]);
        setOrgs(orgsData.organizations || []);
        setRoles(rolesData.roles || []);
        if (orgsData.organizations?.length) {
          setSelectedOrg(orgsData.organizations[0]);
        }
      } catch {
        /* empty */
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (selectedOrg) {
      organizationsApi.getMembers(selectedOrg.id).then((data) => {
        setMembers(data.members || []);
      }).catch(() => setMembers([]));
    }
  }, [selectedOrg]);

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await organizationsApi.create(orgName, orgSlug);
      setOrgs((prev) => [...prev, { ...created, my_role: "admin", is_owner: true } as Organization]);
      setSelectedOrg(created as Organization);
      setShowCreate(false);
      setOrgName("");
      setOrgSlug("");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create organization");
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    try {
      const result = await organizationsApi.invite(selectedOrg.id, inviteEmail, inviteRole);
      setInviteLink(window.location.origin + result.invite_url);
      setInviteEmail("");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to send invitation");
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    if (!selectedOrg) return;
    try {
      await organizationsApi.updateMemberRole(selectedOrg.id, userId, newRole);
      setMembers((prev) =>
        prev.map((m) => (m.user_id === userId ? { ...m, role: newRole } : m))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update role");
    }
  };

  const handleRemove = async (userId: string) => {
    if (!selectedOrg || !confirm("Remove this member?")) return;
    try {
      await organizationsApi.removeMember(selectedOrg.id, userId);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to remove member");
    }
  };

  const getRoleBadgeClass = (role: string) => {
    const map: Record<string, string> = {
      super_admin: "badge-error",
      admin: "badge-warning",
      incubator_manager: "badge-accent",
      innovation_lead: "badge-accent",
      investor_advisor: "badge-info",
      founder: "badge-success",
      founder_product_lead: "badge-success",
      fullstack_engineer: "badge-primary",
      backend_engineer: "badge-primary",
      devops_engineer: "badge-primary",
      ai_engineer: "badge-accent",
      ui_ux_designer: "badge-secondary",
      security_consultant: "badge-error",
      growth_marketing_lead: "badge-info",
      team_member: "badge-info",
      viewer: "",
    };
    return map[role] || "";
  };

  if (loading) {
    return (
      <div className="animate-fade-in">
        <div className="skeleton" style={{ height: 200, borderRadius: "var(--radius-lg)" }} />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <p className={styles.subtitle}>
        Manage your organization, team members, roles, and invitations.
      </p>

      {/* Org Selector + Create */}
      <div className={`${styles.orgHeader} glass-card`}>
        <div className={styles.orgSelector}>
          {orgs.length > 0 ? (
            <div className={styles.orgTabs}>
              {orgs.map((org) => (
                <button
                  key={org.id}
                  className={`${styles.orgTab} ${selectedOrg?.id === org.id ? styles.orgTabActive : ""}`}
                  onClick={() => setSelectedOrg(org)}
                >
                  <span className={styles.orgIcon}>🏢</span>
                  <div>
                    <div className={styles.orgTabName}>{org.name}</div>
                    <div className={styles.orgTabMeta}>
                      <span className={`badge ${getRoleBadgeClass(org.my_role || "viewer")}`}>
                        {(org.my_role || "viewer").replace(/_/g, " ")}
                      </span>
                      <span className="badge">{org.plan}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)", fontSize: "var(--fs-sm)" }}>
              No organizations yet. Create one to start collaborating.
            </p>
          )}
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)} id="create-org-btn">
          + New Organization
        </button>
      </div>

      {/* Create Org Modal */}
      {showCreate && (
        <div className={styles.modalOverlay} onClick={() => setShowCreate(false)}>
          <div className={`${styles.modal} glass-card`} onClick={(e) => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>Create Organization</h3>
            <form onSubmit={handleCreateOrg} className={styles.form}>
              <div>
                <label className="input-label">Name</label>
                <input
                  className="input"
                  value={orgName}
                  onChange={(e) => {
                    setOrgName(e.target.value);
                    setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-").replace(/-+/g, "-"));
                  }}
                  placeholder="My Accelerator"
                  required
                />
              </div>
              <div>
                <label className="input-label">Slug (URL-friendly)</label>
                <input
                  className="input"
                  value={orgSlug}
                  onChange={(e) => setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                  placeholder="my-accelerator"
                  required
                />
              </div>
              <div className={styles.modalActions}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" id="submit-org-btn">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Team Members */}
      {selectedOrg && (
        <>
          <div className={`${styles.membersCard} glass-card`}>
            <div className={styles.membersHeader}>
              <h3 className={styles.sectionTitle}>Team Members</h3>
              {(selectedOrg.my_role === "admin" || selectedOrg.my_role === "super_admin" || selectedOrg.my_role === "incubator_manager") && (
                <button className="btn btn-primary" onClick={() => { setShowInvite(true); setInviteLink(""); }} id="invite-btn">
                  ✉️ Invite Member
                </button>
              )}
            </div>

            {members.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "var(--fs-sm)", textAlign: "center", padding: "var(--space-6)" }}>
                No members yet. Invite your team to get started.
              </p>
            ) : (
              <div className={styles.membersList}>
                {members.map((member) => (
                  <div key={member.id} className={styles.memberRow}>
                    <div className={styles.memberAvatar}>
                      {member.avatar_url ? (
                        <img src={member.avatar_url} alt="" />
                      ) : (
                        <span>{(member.full_name || "U")[0].toUpperCase()}</span>
                      )}
                    </div>
                    <div className={styles.memberInfo}>
                      <div className={styles.memberName}>{member.full_name || "Unknown"}</div>
                      <div className={styles.memberMeta}>Joined {new Date(member.joined_at).toLocaleDateString()}</div>
                    </div>
                    {selectedOrg.my_role === "admin" || selectedOrg.my_role === "super_admin" || selectedOrg.my_role === "incubator_manager" ? (
                      <>
                        <select
                          className={styles.roleSelect}
                          value={member.role}
                          onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                        >
                          {roles.map((r) => (
                            <option key={r.id} value={r.id}>{r.label}</option>
                          ))}
                        </select>
                        <button
                          className={styles.removeBtn}
                          onClick={() => handleRemove(member.user_id)}
                          title="Remove member"
                        >
                          ✕
                        </button>
                      </>
                    ) : (
                      <span className={`badge ${getRoleBadgeClass(member.role)}`} style={{ marginLeft: "auto", marginRight: "var(--space-4)" }}>
                        {member.role.replace(/_/g, " ")}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Role Legend */}
          <div className={`${styles.rolesLegend} glass-card`}>
            <h3 className={styles.sectionTitle}>Role Hierarchy</h3>
            <div className={styles.rolesGrid}>
              {roles.map((role) => (
                <div key={role.id} className={styles.roleCard}>
                  <div className={styles.roleHeader}>
                    <span className={`badge ${getRoleBadgeClass(role.id)}`}>{role.label}</span>
                    <span className={styles.roleLevel}>Level {role.level}</span>
                  </div>
                  <p className={styles.roleDesc}>{role.description}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Invite Modal */}
      {showInvite && (
        <div className={styles.modalOverlay} onClick={() => setShowInvite(false)}>
          <div className={`${styles.modal} glass-card`} onClick={(e) => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>Invite Team Member</h3>
            {inviteLink ? (
              <div className={styles.inviteSuccess}>
                <p>✅ Invitation created! Share this link:</p>
                <div className={styles.inviteLinkBox}>
                  <code>{inviteLink}</code>
                  <button
                    className="btn btn-secondary"
                    onClick={() => navigator.clipboard.writeText(inviteLink)}
                  >
                    Copy
                  </button>
                </div>
                <button className="btn btn-primary" onClick={() => setShowInvite(false)} style={{ marginTop: "var(--space-4)" }}>
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleInvite} className={styles.form}>
                <div>
                  <label className="input-label">Email Address</label>
                  <input
                    className="input"
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="teammate@example.com"
                    required
                  />
                </div>
                <div>
                  <label className="input-label">Role</label>
                  <select
                    className="input"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                  >
                    {roles.filter((r) => r.level < 70).map((r) => (
                      <option key={r.id} value={r.id}>{r.label} — {r.description}</option>
                    ))}
                  </select>
                </div>
                <div className={styles.modalActions}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowInvite(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary" id="send-invite-btn">Send Invitation</button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
