"use client";

import { useState, useEffect, useMemo } from "react";
import styles from "./team.module.css";
import { organizationsApi, type Organization, type OrgMember, type RoleInfo } from "@/lib/api";

export default function TeamPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [showInvite, setShowInvite] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createType, setCreateType] = useState<"root" | "child">("root");
  
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);

  // Invite form state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("team_member");
  const [inviteLink, setInviteLink] = useState("");
  const [inviting, setInviting] = useState(false);

  // Creation form
  const [newOrgName, setNewOrgName] = useState("");
  const [parentOrgIdForNew, setParentOrgIdForNew] = useState<string | null>(null);

  const [childMembersCache, setChildMembersCache] = useState<Record<string, OrgMember[]>>({});

  useEffect(() => {
    async function load() {
      try {
        const profileStr = localStorage.getItem("user_profile");
        if (profileStr) {
          const profile = JSON.parse(profileStr);
          setIsSuperAdmin(profile.platform_role === "super_admin");
        }

        const [orgsData, rolesData] = await Promise.all([
          organizationsApi.list(),
          organizationsApi.getRoles(),
        ]);
        
        setOrgs(orgsData.organizations || []);
        setRoles(rolesData.roles || []);
        
        if (orgsData.organizations && orgsData.organizations.length > 0) {
          const roots = orgsData.organizations.filter(o => !o.parent_id);
          if (roots.length > 0) setSelectedOrgId(roots[0].id);
          else setSelectedOrgId(orgsData.organizations[0].id);
        }
      } catch (err) {
        console.error("Failed to load platform data:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const rootOrgs = useMemo(() => orgs.filter(o => !o.parent_id), [orgs]);
  const childOrgs = useMemo(() => orgs.filter(o => o.parent_id), [orgs]);
  const selectedOrg = useMemo(() => orgs.find(o => o.id === selectedOrgId), [orgs, selectedOrgId]);

  useEffect(() => {
    if (selectedOrgId) {
      if (selectedOrg && !selectedOrg.parent_id) {
        // If it's a root org, fetch its own members (if any) and trigger fetches for its children
        organizationsApi.getMembers(selectedOrgId)
          .then(data => setMembers(data.members || []))
          .catch(console.error);

        const childrenOfRoot = childOrgs.filter(c => c.parent_id === selectedOrgId);
        childrenOfRoot.forEach(child => {
          organizationsApi.getMembers(child.id)
            .then(data => {
              setChildMembersCache(prev => ({ ...prev, [child.id]: data.members || [] }));
            })
            .catch(err => {
              console.error("Child org member fetch failed (likely auth):", err);
            });
        });
      } else {
        // Just a regular child org
        organizationsApi.getMembers(selectedOrgId)
          .then(data => setMembers(data.members || []))
          .catch(console.error);
      }
    } else {
      setMembers([]);
    }
  }, [selectedOrgId, selectedOrg, childOrgs]);

  // Governance Logic Check
  const myRoleInSelected = selectedOrg?.my_role;
  const isSelectedAdmin = myRoleInSelected === "admin" || myRoleInSelected === "incubator_manager";
  
  // ai.org (root) can create new org (child)
  const canCreateDept = selectedOrg && !selectedOrg.parent_id && !isSuperAdmin && isSelectedAdmin;
  
  // created org (child) can only invite members
  const canInvite = selectedOrg && selectedOrg.parent_id && !isSuperAdmin && isSelectedAdmin;

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName) return;
    try {
      const slug = newOrgName.toLowerCase().replace(/ /g, "-");
      const created = await organizationsApi.create(newOrgName, slug, parentOrgIdForNew || undefined);
      setOrgs(prev => [...prev, created as Organization]);
      setShowCreate(false);
      setNewOrgName("");
    } catch (err) {
      alert("Failed to create organization. Check permissions.");
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrgId) return;
    setInviting(true);
    try {
      const result = await organizationsApi.invite(selectedOrgId, inviteEmail, inviteRole);
      setInviteLink(window.location.origin + result.invite_url);
      setInviteEmail("");
      const data = await organizationsApi.getMembers(selectedOrgId);
      setMembers(data.members || []);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to send invitation");
    } finally {
      setInviting(false);
    }
  };

  if (loading) return <div className="loader" />;

  return (
    <div className={styles.teamPage}>
      <div className={styles.header}>
        <h1 className={styles.title}>Team & Organization</h1>
        <p className={styles.subtitle}>Manage your organization, team members, roles, and invitations.</p>
      </div>

      {orgs.length === 0 ? (
        <div className={styles.genesisContainer}>
          <h2 className={styles.genesisTitle}>Platform Genesis</h2>
          <p className={styles.genesisText}>
            Your database is clean. Initialize your root organization (e.g. ai.org) to start building out your enterprise tree.
          </p>
          {isSuperAdmin && (
             <button className="btn btn-primary" onClick={() => { setCreateType("root"); setParentOrgIdForNew(null); setShowCreate(true); }}>
               🚀 Initialize Root Hub
             </button>
          )}
        </div>
      ) : (
        <>
          {/* Top Level: Root Organizations (Super Admins OR members of a Root Org) */}
          {(isSuperAdmin || rootOrgs.length > 0) && (
            <>
              <div className={styles.sectionLabel}>Corporate Hubs</div>
              <div className={`${styles.orgGrid} ${styles.rootGrid}`}>
                {rootOrgs.map(org => (
                  <div 
                    key={org.id} 
                    className={`${styles.orgCard} ${styles.rootCard} ${selectedOrgId === org.id ? styles.selected : ""}`}
                    onClick={() => setSelectedOrgId(org.id)}
                  >
                    <div className={styles.orgIcon}>🏢</div>
                    <div className={styles.orgInfo}>
                      <div className={styles.orgName}>{org.name}</div>
                      <div className={styles.orgBadges}>
                        <span className={styles.roleBadge}>HUB</span>
                        <span className={styles.planBadge}>{org.plan}</span>
                      </div>
                    </div>
                  </div>
                ))}
                {isSuperAdmin && (
                  <div 
                    className={styles.addOrgBtn}
                    onClick={() => { setCreateType("root"); setParentOrgIdForNew(null); setShowCreate(true); }}
                  >
                    + New Hub
                  </div>
                )}
              </div>
            </>
          )}

          {/* Child Level: Departments / Enterprises */}
          {(isSuperAdmin || childOrgs.length > 0) && (
            <>
              <div className={styles.sectionLabel}>Departments & Teams</div>
              <div className={styles.orgGrid}>
                {childOrgs.map(org => (
              <div 
                key={org.id} 
                className={`${styles.orgCard} ${selectedOrgId === org.id ? styles.selected : ""}`}
                onClick={() => setSelectedOrgId(org.id)}
              >
                <div className={styles.orgIcon}>📁</div>
                <div className={styles.orgInfo}>
                  <div className={styles.orgName}>{org.name}</div>
                  <div className={styles.orgBadges}>
                    <span className={styles.roleBadge}>{org.my_role?.replace(/_/g, " ")}</span>
                    <span className={styles.planBadge}>DEPARTMENT</span>
                  </div>
                  {org.parent_id && (
                    <div style={{ fontSize: "0.65rem", color: "var(--color-gray-500)", marginTop: "4px" }}>
                      Managed by {rootOrgs.find(r => r.id === org.parent_id)?.name || "Corporate Hub"}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          </>
          )}
        </>
      )}

      {/* Details Section for Selected Org */}
      {selectedOrg && (
        <div className={styles.detailsSection}>
          <div className={styles.sectionHeader}>
            <div>
              <h3 className={styles.sectionTitle}>Enterprise SSO Configuration (SAML/OIDC)</h3>
              <p className={styles.subtitle}>Configure IdP endpoints for {selectedOrg.name}</p>
            </div>
          </div>
          
          <form style={{ marginBottom: "2rem", paddingBottom: "2rem", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <div className="form-group-row" style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label style={{ fontSize: "0.8rem", color: "var(--color-gray-400)", display: "block", marginBottom: "4px" }}>Provider Name</label>
                <input className="input" placeholder="e.g. okta, azure_ad" disabled={isSuperAdmin} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label style={{ fontSize: "0.8rem", color: "var(--color-gray-400)", display: "block", marginBottom: "4px" }}>Entity ID</label>
                <input className="input" placeholder="IdP Entity ID" disabled={isSuperAdmin} />
              </div>
            </div>
            
            <div className="form-group-row" style={{ display: "flex", gap: "1rem", alignItems: "flex-end" }}>
               <div className="form-group" style={{ flex: 1.5 }}>
                 <label style={{ fontSize: "0.8rem", color: "var(--color-gray-400)", display: "block", marginBottom: "4px" }}>ACS URL</label>
                 <input className="input" placeholder="Assertion Consumer Service URL" disabled={isSuperAdmin} />
               </div>
               <div className="form-group" style={{ flex: 1, display: "flex", alignItems: "center", gap: "8px", height: "40px" }}>
                 <input type="checkbox" id="sso_enforce" disabled={isSuperAdmin} />
                 <label htmlFor="sso_enforce" style={{ color: "white", fontSize: "0.9rem" }}>Enforce SSO Login for all members</label>
               </div>
            </div>

            {!isSuperAdmin && (
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "1rem" }}>
                <button type="button" className="btn btn-primary" style={{ padding: "0.5rem 1.5rem" }}>Save SSO Settings</button>
              </div>
            )}
          </form>

          {/* Members / Infrastructure Render */}
          {!selectedOrg.parent_id ? (
             <>
               <div className={styles.sectionHeader}>
                 <div>
                   <h3 className={styles.sectionTitle}>Hub Infrastructure</h3>
                   <p className={styles.subtitle}>Overview of all departments and members under {selectedOrg.name}.</p>
                 </div>
                 {canCreateDept && (
                   <button 
                     className="btn btn-primary"
                     onClick={() => { 
                       setCreateType("child"); 
                       setParentOrgIdForNew(selectedOrg.id); // Bind specifically to this selected Hub
                       setShowCreate(true); 
                     }}
                   >
                     + Create Department
                   </button>
                 )}
               </div>

               {childOrgs.filter(c => c.parent_id === selectedOrg.id).length === 0 ? (
                 <p style={{ color: "var(--color-gray-500)", padding: "1rem", fontStyle: "italic" }}>No departments currently assigned under this Hub.</p>
               ) : (
                 childOrgs.filter(c => c.parent_id === selectedOrg.id).map(child => (
                   <div key={child.id} style={{ marginBottom: "2rem", background: "rgba(0,0,0,0.2)", padding: "1.5rem", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.05)" }}>
                     <h4 style={{ color: "var(--color-white)", margin: "0 0 1rem 0", fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "8px" }}>
                       📁 {child.name} 
                       <span style={{ fontSize: "0.7rem", padding: "2px 6px", background: "rgba(16, 185, 129, 0.1)", color: "#10b981", borderRadius: "4px" }}>DEPARTMENT</span>
                     </h4>
                     <div className={styles.membersList}>
                       {(childMembersCache[child.id] || []).length === 0 ? (
                         <p style={{ color: "var(--color-gray-500)", padding: "0.5rem" }}>No active members.</p>
                       ) : (
                         (childMembersCache[child.id] || []).map(m => (
                           <div key={m.user_id} className={styles.memberRow}>
                             <div className={styles.memberInfo}>
                               <div className={styles.memberAvatar}>👤</div>
                               <div className={styles.memberName}>{m.full_name || "Unknown User"}</div>
                               <div className={styles.memberRole}>{m.role.replace(/_/g, " ")}</div>
                             </div>
                           </div>
                         ))
                       )}
                     </div>
                   </div>
                 ))
               )}
             </>
          ) : (
             <>
               <div className={styles.sectionHeader}>
                 <div>
                   <h3 className={styles.sectionTitle}>Members of {selectedOrg.name}</h3>
                   <p className={styles.subtitle}>
                     {isSuperAdmin 
                         ? "Super Admins can view members but cannot invite."
                         : "Manage your department's human capital below."}
                   </p>
                 </div>
                 {canInvite && (
                   <button 
                     className="btn btn-primary"
                     onClick={() => { setShowInvite(true); setInviteLink(""); }}
                   >
                     + Invite Member
                   </button>
                 )}
               </div>

               <div className={styles.membersList}>
                 {members.length === 0 ? (
                   <p style={{ color: "var(--color-gray-500)", padding: "1rem" }}>No members found in this unit.</p>
                 ) : (
                   members.map(m => (
                     <div key={m.user_id} className={styles.memberRow}>
                       <div className={styles.memberInfo}>
                         <div className={styles.memberAvatar}>👤</div>
                         <div className={styles.memberName}>{m.full_name || "Unknown User"}</div>
                         <div className={styles.memberRole}>{m.role.replace(/_/g, " ")}</div>
                       </div>
                     </div>
                   ))
                 )}
               </div>
             </>
          )}
        </div>
      )}

      {/* Modals */}
      {showInvite && canInvite && (
        <div className={styles.modalOverlay} onClick={() => setShowInvite(false)}>
          <div className={`${styles.modal} glass-card`} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>Invite to {selectedOrg?.name}</h3>
            {inviteLink ? (
              <div className={styles.successBox}>
                <p>Link generated! Send this to the member:</p>
                <code>{inviteLink}</code>
                <button className="btn btn-primary" style={{marginTop: 16}} onClick={() => setShowInvite(false)}>Done</button>
              </div>
            ) : (
              <form onSubmit={handleSendInvite}>
                <div className="form-group">
                  <label>Email Address</label>
                  <input className="input" type="email" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} required />
                </div>
                <div className="form-group" style={{marginTop: 16}}>
                  <label>Role</label>
                  <select className="input" value={inviteRole} onChange={e => setInviteRole(e.target.value)}>
                    {roles.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}
                  </select>
                </div>
                <div className={styles.modalActions}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowInvite(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary" disabled={inviting}>
                    {inviting ? "Sending..." : "Send Invitation"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {showCreate && (
        <div className={styles.modalOverlay} onClick={() => setShowCreate(false)}>
          <div className={`${styles.modal} glass-card`} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>
              {createType === "root" ? "Create Root Hub" : "Create Department"}
            </h3>
            <form onSubmit={handleCreateOrg}>
              <div className="form-group">
                <label>Name</label>
                <input className="input" value={newOrgName} onChange={e => setNewOrgName(e.target.value)} placeholder={createType === "root" ? "e.g. ai.org" : "e.g. Finance"} required />
              </div>

              {createType === "child" && rootOrgs.length > 0 && (
                <div className="form-group" style={{marginTop: 16}}>
                  <label>Parent Hub</label>
                  <select className="input" value={parentOrgIdForNew || ""} onChange={e => setParentOrgIdForNew(e.target.value)}>
                    {rootOrgs.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
              )}

              <div className={styles.modalActions}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Structure</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
