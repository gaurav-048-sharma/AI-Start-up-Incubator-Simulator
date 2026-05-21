"use client";

import { useState, useEffect, useMemo } from "react";
import styles from "./team.module.css";
import { authApi, organizationsApi, setActiveOrg, type Organization, type OrgMember, type RoleInfo } from "@/lib/api";

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
  const [actionError, setActionError] = useState<string | null>(null);
  const [canCreateAllowed, setCanCreateAllowed] = useState<boolean | null>(null);
  const [canInviteAllowed, setCanInviteAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const me = await authApi.me();
        setIsSuperAdmin(me.platform_role === "super_admin");

        const [orgsData, rolesData] = await Promise.all([
          organizationsApi.list(),
          organizationsApi.getRoles(),
        ]);
        
        setOrgs(orgsData.organizations || []);
        setRoles(rolesData.roles || []);
        
        if (orgsData.organizations && orgsData.organizations.length > 0) {
          const preferred = orgsData.organizations.find(o => o.id === me.current_org_id)
            || orgsData.organizations.find(o => !o.parent_id)
            || orgsData.organizations[0];
          if (preferred) setSelectedOrgId(preferred.id);
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
      setActiveOrg(selectedOrgId);

      // Refresh authoritative org details (my_role, member_count)
      organizationsApi.get(selectedOrgId)
        .then((orgData: Organization) => {
          setOrgs(prev => {
            const found = prev.find(o => o.id === orgData.id);
            if (found) return prev.map(p => (p.id === orgData.id ? { ...p, ...orgData } : p));
            return [...prev, orgData as Organization];
          });

          const role = orgData.my_role;
          const isAdmin = role === "admin" || role === "incubator_manager" || role === "workspace_owner";
          setCanCreateAllowed(Boolean(orgData && !orgData.parent_id && isAdmin && !isSuperAdmin));
          setCanInviteAllowed(Boolean(orgData && orgData.parent_id && isAdmin && !isSuperAdmin));
        })
        .catch(err => {
          console.error("Failed to refresh org details:", err);
        });

      // Fetch members for the selected org
      organizationsApi.getMembers(selectedOrgId)
        .then(data => setMembers(data.members || []))
        .catch(console.error);

      // If selected is a root, fetch child members as well
      if (selectedOrg && !selectedOrg.parent_id) {
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
      }
    } else {
      // Defer clearing to avoid synchronous setState in an effect
      setTimeout(() => {
        setMembers([]);
        setCanCreateAllowed(null);
        setCanInviteAllowed(null);
      }, 0);
    }
  }, [selectedOrgId, selectedOrg, childOrgs, isSuperAdmin]);


  // Clear previous action errors when selection changes (deferred)
  useEffect(() => {
    if (selectedOrgId) setTimeout(() => setActionError(null), 0);
  }, [selectedOrgId]);

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

    // SECURITY GUARD: Only super_admin can create root organizations
    if (createType === "root" && !isSuperAdmin) {
      alert("Only platform administrators can create root hubs. Please submit an enterprise request for official onboarding.");
      setShowCreate(false);
      return;
    }

    setActionError(null);
    try {
      const slug = newOrgName.toLowerCase().replace(/ /g, "-");
      const created = await organizationsApi.create(newOrgName, slug, parentOrgIdForNew || undefined);
      setOrgs(prev => [...prev, created as Organization]);
      setShowCreate(false);
      setNewOrgName("");
      setCanCreateAllowed(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create organization";
      setActionError(msg);
      if (msg.toLowerCase().includes("403") || msg.toLowerCase().includes("access denied") || msg.toLowerCase().includes("requires")) {
        setCanCreateAllowed(false);
      }
      alert(msg);
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrgId) return;
    setInviting(true);
    setActionError(null);
    try {
      const result = await organizationsApi.invite(selectedOrgId, inviteEmail, inviteRole);
      setInviteLink(window.location.origin + result.invite_url);
      setInviteEmail("");
      const data = await organizationsApi.getMembers(selectedOrgId);
      setMembers(data.members || []);
      setCanInviteAllowed(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to send invitation";
      setActionError(msg);
      if (msg.toLowerCase().includes("403") || msg.toLowerCase().includes("access denied") || msg.toLowerCase().includes("invite")) {
        setCanInviteAllowed(false);
      }
      alert(msg);
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
                        {typeof org.member_count !== "undefined" && (
                            <span className={styles.countBadge}>{org.member_count} members</span>
                          )}
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
                  {typeof org.member_count !== "undefined" && (
                    <div className={styles.metaTextSmall}>
                      {org.member_count} members
                    </div>
                  )}
                  {org.parent_id && (
                    <div className={styles.metaTextTiny}>
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
            {actionError && (
              <div className={styles.actionError}>{actionError}</div>
            )}
          <div className={styles.sectionHeader}>
            <div>
              <h3 className={styles.sectionTitle}>Enterprise SSO Configuration (SAML/OIDC)</h3>
              <p className={styles.subtitle}>Configure IdP endpoints for {selectedOrg.name}</p>
            </div>
          </div>
          
          <form className={styles.ssoForm}>
            <div className={styles.formRow}>
              <div className={`form-group ${styles.formGroupFlex1}`}>
                <label className={styles.labelMuted} htmlFor="sso_provider">Provider Name</label>
                <input id="sso_provider" className="input" placeholder="e.g. okta, azure_ad" disabled={isSuperAdmin} />
              </div>
              <div className={`form-group ${styles.formGroupFlex1}`}>
                <label className={styles.labelMuted} htmlFor="sso_entity">Entity ID</label>
                <input id="sso_entity" className="input" placeholder="IdP Entity ID" disabled={isSuperAdmin} />
              </div>
            </div>
            
            <div className={`${styles.formRow} ${styles.formRowEnd}`}>
              <div className={`form-group ${styles.formGroupFlex1_5}`}>
                 <label className={styles.labelMuted} htmlFor="sso_acs">ACS URL</label>
                 <input id="sso_acs" className="input" placeholder="Assertion Consumer Service URL" disabled={isSuperAdmin} />
               </div>
               <div className={`form-group ${styles.formGroupFlex1} ${styles.formGroupInlineCenter}`}>
                 <input type="checkbox" id="sso_enforce" disabled={isSuperAdmin} />
                 <label htmlFor="sso_enforce" className={styles.ssoEnforceLabel}>Enforce SSO Login for all members</label>
               </div>
            </div>

            {!isSuperAdmin && (
              <div className={styles.ssoSaveWrap}>
                <button type="button" className={`btn btn-primary ${styles.ssoSaveBtn}`}>Save SSO Settings</button>
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
                 {canCreateDept && canCreateAllowed !== false && (
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
                 {canCreateDept && canCreateAllowed === false && (
                   <button className="btn btn-secondary" disabled title="You don't have permission to create a department here">Create Department (no permission)</button>
                 )}
               </div>

               {childOrgs.filter(c => c.parent_id === selectedOrg.id).length === 0 ? (
                 <p className={styles.emptyNote}>No departments currently assigned under this Hub.</p>
               ) : (
                 childOrgs.filter(c => c.parent_id === selectedOrg.id).map(child => (
                   <div key={child.id} className={styles.childCard}>
                     <h4 className={styles.childHeader}>
                       📁 {child.name} 
                       <span className={styles.departmentBadge}>DEPARTMENT</span>
                     </h4>
                     <div className={styles.membersList}>
                       {(childMembersCache[child.id] || []).length === 0 ? (
                         <p className={styles.noActiveMembers}>No active members.</p>
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
                 {canInvite && canInviteAllowed !== false && (
                   <button 
                     className="btn btn-primary"
                     onClick={() => { setShowInvite(true); setInviteLink(""); }}
                   >
                     + Invite Member
                   </button>
                 )}
                 {canInvite && canInviteAllowed === false && (
                   <button className="btn btn-secondary" disabled title="You don't have permission to invite members here">Invite Member (no permission)</button>
                 )}
               </div>

               <div className={styles.membersList}>
                 {members.length === 0 ? (
                   <p className={styles.emptyNote}>No members found in this unit.</p>
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
                <button className={`btn btn-primary ${styles.doneBtnMargin}`} onClick={() => setShowInvite(false)}>Done</button>
              </div>
            ) : (
              <form onSubmit={handleSendInvite}>
                <div className="form-group">
                  <label htmlFor="invite_email">Email Address</label>
                  <input id="invite_email" className="input" type="email" placeholder="user@example.com" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} required />
                </div>
                <div className={`form-group ${styles.formGroupMarginTop}`}>
                  <label htmlFor="invite_role">Role</label>
                  <select id="invite_role" className="input" value={inviteRole} onChange={e => setInviteRole(e.target.value)}>
                    {roles.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}
                  </select>
                </div>
                <div className={styles.modalActions}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowInvite(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary" disabled={inviting || canInviteAllowed === false}>
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
                <label htmlFor="new_org_name">Name</label>
                <input id="new_org_name" className="input" value={newOrgName} onChange={e => setNewOrgName(e.target.value)} placeholder={createType === "root" ? "e.g. ai.org" : "e.g. Finance"} required />
              </div>

              {createType === "child" && rootOrgs.length > 0 && (
                <div className={`form-group ${styles.formGroupMarginTop}`}>
                  <label htmlFor="parent_hub">Parent Hub</label>
                  <select id="parent_hub" className="input" value={parentOrgIdForNew || ""} onChange={e => setParentOrgIdForNew(e.target.value)}>
                    {rootOrgs.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
              )}

              <div className={styles.modalActions}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={createType === "child" && canCreateAllowed === false}>Create Structure</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
