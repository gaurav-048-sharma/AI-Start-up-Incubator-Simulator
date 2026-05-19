const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  /** Skip org context injection (for platform-level routes) */
  skipOrgContext?: boolean;
}

/**
 * Core API request function.
 * Automatically injects:
 *   - Authorization header from Supabase JWT
 *   - X-Org-Id header from localStorage (for tenant-scoped requests)
 */
export async function apiRequest<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, skipOrgContext = false } = options;

  // Resolve active org from localStorage (Slack/GitHub-style multi-org switching)
  const activeOrgId =
    !skipOrgContext && typeof window !== "undefined"
      ? localStorage.getItem("activeOrgId")
      : null;

  const config: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(activeOrgId ? { "X-Org-Id": activeOrgId } : {}),
      ...headers,
    },
  };

  // Inject Supabase JWT
  if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SUPABASE_URL) {
    try {
      const { createClient } = await import("./supabase/client");
      const supabase = createClient();
      if (supabase) {
        const { data } = await supabase.auth.getSession();
        if (data?.session?.access_token) {
          (config.headers as Record<string, string>)["Authorization"] = `Bearer ${data.session.access_token}`;
        }
      }
    } catch {
      // Ignore
    }
  }

  if (body) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// ── Org Context Helpers ─────────────────────────────────────────

/** Set the active organization for multi-tab safe context switching */
export function setActiveOrg(orgId: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("activeOrgId", orgId);
    // Dispatch storage event for cross-tab sync
    window.dispatchEvent(new StorageEvent("storage", { key: "activeOrgId", newValue: orgId }));
  }
}

/** Get the current active organization ID */
export function getActiveOrgId(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("activeOrgId");
  }
  return null;
}

/** Clear active org context */
export function clearActiveOrg() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("activeOrgId");
  }
}


// ── Ideas API ────────────────────────────────────────────────────
export const ideasApi = {
  list: () => apiRequest<{ ideas: Idea[]; total: number }>("/api/ideas"),
  get: (id: string) => apiRequest<Idea>(`/api/ideas/${id}`),
  create: (data: IdeaCreate) => apiRequest<Idea>("/api/ideas", { method: "POST", body: data }),
  update: (id: string, data: Partial<IdeaCreate>) =>
    apiRequest<Idea>(`/api/ideas/${id}`, { method: "PUT", body: data }),
  delete: (id: string) => apiRequest<void>(`/api/ideas/${id}`, { method: "DELETE" }),
  launch: (id: string) =>
    apiRequest<{ idea_id: string; status: string; message: string }>(`/api/ideas/${id}/launch`, { method: "POST" }),
};

// ── Agents API ───────────────────────────────────────────────────
export const agentsApi = {
  getActivities: (ideaId: string) => apiRequest<AgentActivity[]>(`/api/agents/ideas/${ideaId}/activities`),
  getRoles: () => apiRequest<{ roles: AgentRole[] }>("/api/agents/roles"),
  runSingle: (ideaId: string, role: string) =>
    apiRequest<{ agent_role: string; output: string }>(`/api/agents/ideas/${ideaId}/run/${role}`, { method: "POST" }),
};

// ── Workflows API ────────────────────────────────────────────────
export const workflowsApi = {
  getState: (ideaId: string) => apiRequest<WorkflowState>(`/api/workflows/ideas/${ideaId}/state`),
  getGraph: () => apiRequest<WorkflowGraph>("/api/workflows/graph"),
  retry: (ideaId: string) =>
    apiRequest<{ message: string }>(`/api/workflows/ideas/${ideaId}/retry`, { method: "POST" }),
};

// ── Reports API ──────────────────────────────────────────────────
export const reportsApi = {
  listForIdea: (ideaId: string) => apiRequest<Report[]>(`/api/reports/ideas/${ideaId}`),
  get: (reportId: string) => apiRequest<Report>(`/api/reports/${reportId}`),
};

// ── Simulations API ──────────────────────────────────────────────
export const simulationsApi = {
  start: (ideaId: string) =>
    apiRequest<Simulation>(`/api/simulations/ideas/${ideaId}/simulate`, { method: "POST" }),
  get: (simId: string) => apiRequest<Simulation>(`/api/simulations/${simId}`),
  listForIdea: (ideaId: string) =>
    apiRequest<{ simulations: Simulation[] }>(`/api/simulations/ideas/${ideaId}/list`),
};

// ── Analytics API ────────────────────────────────────────────────
export const analyticsApi = {
  getUsage: (days: number = 30) =>
    apiRequest<UsageSummary>(`/api/analytics/usage?days=${days}`),
  getCredits: () =>
    apiRequest<{ credits: number; user_id: string }>("/api/analytics/credits"),
  checkCredits: (eventType: string) =>
    apiRequest<{ has_credits: boolean; required: number }>(`/api/analytics/credits/check?event_type=${eventType}`),
};

// ── Notifications API ────────────────────────────────────────────
export const notificationsApi = {
  list: (unreadOnly: boolean = false) =>
    apiRequest<{ notifications: Notification[]; unread_count: number; total: number }>(
      `/api/notifications?unread_only=${unreadOnly}`
    ),
  getUnreadCount: () =>
    apiRequest<{ unread_count: number }>("/api/notifications/unread-count"),
  markRead: (id: string) =>
    apiRequest<{ success: boolean }>(`/api/notifications/${id}/read`, { method: "PATCH" }),
  markAllRead: () =>
    apiRequest<{ success: boolean }>("/api/notifications/mark-all-read", { method: "POST" }),
  delete: (id: string) =>
    apiRequest<{ success: boolean }>(`/api/notifications/${id}`, { method: "DELETE" }),
};

// ── Settings API ─────────────────────────────────────────────────
export const settingsApi = {
  get: () => apiRequest<UserSettings>("/api/settings"),
  update: (data: Partial<UserSettings>) =>
    apiRequest<UserSettings>("/api/settings", { method: "PATCH", body: data }),
};

// ── Comparison API ───────────────────────────────────────────────
export const comparisonApi = {
  compare: (ideaIds: string[]) =>
    apiRequest<ComparisonResult>("/api/ideas/compare", {
      method: "POST",
      body: { idea_ids: ideaIds },
    }),
};

// ── Organizations API (Tenant-scoped) ────────────────────────────
export const organizationsApi = {
  list: () =>
    apiRequest<{ organizations: Organization[] }>("/api/organizations"),
  get: (orgId: string) =>
    apiRequest<Organization>(`/api/organizations/${orgId}`),
  create: (name: string, slug: string) =>
    apiRequest<Organization>("/api/organizations", {
      method: "POST",
      body: { name, slug },
    }),
  getRoles: () =>
    apiRequest<{ roles: RoleInfo[] }>("/api/organizations/roles"),
  getMembers: (orgId: string) =>
    apiRequest<{ members: OrgMember[] }>(`/api/organizations/${orgId}/members`),
  updateMemberRole: (orgId: string, userId: string, role: string) =>
    apiRequest<{ success: boolean }>(`/api/organizations/${orgId}/members/${userId}/role`, {
      method: "PATCH",
      body: { role },
    }),
  updateSSO: (orgId: string, ssoData: Record<string, unknown>) =>
    apiRequest<{ success: boolean }>(`/api/organizations/${orgId}/sso`, {
      method: "PATCH",
      body: ssoData,
    }),
  removeMember: (orgId: string, userId: string) =>
    apiRequest<{ success: boolean }>(`/api/organizations/${orgId}/members/${userId}`, {
      method: "DELETE",
    }),
  invite: (orgId: string, email: string, role: string) =>
    apiRequest<{ invitation_id: string; token: string; invite_url: string }>(
      `/api/organizations/${orgId}/invitations`,
      { method: "POST", body: { email, role } }
    ),
  acceptInvite: (token: string) =>
    apiRequest<{ success: boolean; organization_id: string }>(
      `/api/organizations/invitations/${token}/accept`,
      { method: "POST" }
    ),
  getAuditLog: (orgId: string, limit: number = 50) =>
    apiRequest<{ audit_log: AuditEntry[]; total: number }>(
      `/api/organizations/${orgId}/audit?limit=${limit}`
    ),
};

// ── Billing API ──────────────────────────────────────────────────
export const billingApi = {
  getPlans: () =>
    apiRequest<{ plans: BillingPlan[] }>("/api/billing/plans"),
  getStatus: () =>
    apiRequest<BillingStatus>("/api/billing/status"),
  createCheckout: (tier: string, orgId?: string) =>
    apiRequest<{ checkout_url: string; session_id: string }>("/api/billing/checkout", {
      method: "POST",
      body: {
        tier,
        org_id: orgId,
        success_url: `${typeof window !== "undefined" ? window.location.origin : ""}/dashboard/settings?billing=success`,
        cancel_url: `${typeof window !== "undefined" ? window.location.origin : ""}/dashboard/settings?billing=cancel`,
      },
    }),
};

// ── Platform Admin API ───────────────────────────────────────────
// These endpoints skip org context injection — they are platform-scoped.
export const adminApi = {
  // Enterprise requests
  listEnterpriseRequests: () =>
    apiRequest<{ requests: EnterpriseRequest[] }>("/api/admin/requests", { skipOrgContext: true }),
  approveEnterpriseRequest: (requestId: string) =>
    apiRequest<{ status: string; checkout_url: string }>(`/api/admin/approve/${requestId}`, {
      method: "POST",
      skipOrgContext: true,
    }),
  rejectEnterpriseRequest: (requestId: string) =>
    apiRequest<{ status: string }>(`/api/admin/reject/${requestId}`, {
      method: "POST",
      skipOrgContext: true,
    }),

  // Global org management
  listAllOrganizations: () =>
    apiRequest<{ organizations: Organization[] }>("/api/admin/organizations", { skipOrgContext: true }),
  deleteOrganization: (orgId: string) =>
    apiRequest<{ status: string }>(`/api/admin/organizations/${orgId}`, {
      method: "DELETE",
      skipOrgContext: true,
    }),
  updateOrgStatus: (orgId: string, status: "active" | "suspended") =>
    apiRequest<{ status: string }>(`/api/admin/organizations/${orgId}/status`, {
      method: "PATCH",
      body: { status },
      skipOrgContext: true,
    }),

  // Platform user management
  listUsers: (limit: number = 100) =>
    apiRequest<{ users: PlatformUser[] }>(`/api/admin/users?limit=${limit}`, { skipOrgContext: true }),
  updatePlatformRole: (userId: string, platformRole: string) =>
    apiRequest<{ status: string }>(`/api/admin/users/${userId}/platform-role`, {
      method: "PATCH",
      body: { platform_role: platformRole },
      skipOrgContext: true,
    }),
};

// ── MFA API ───────────────────────────────────────────────────────
export const mfaApi = {
  /** List enrolled MFA factors */
  listFactors: () =>
    apiRequest<MfaFactorsResponse>("/api/auth/mfa/factors"),

  /** Get quick MFA status for current user */
  getStatus: () =>
    apiRequest<MfaStatusResponse>("/api/auth/mfa/status"),

  /** Begin TOTP enrollment — returns QR code */
  enroll: (friendlyName?: string) =>
    apiRequest<MfaEnrollResponse>("/api/auth/mfa/enroll", {
      method: "POST",
      body: { friendly_name: friendlyName || "Authenticator App" },
    }),

  /** Verify TOTP code to complete enrollment */
  verify: (factorId: string, code: string) =>
    apiRequest<MfaVerifyResponse>("/api/auth/mfa/verify", {
      method: "POST",
      body: { factor_id: factorId, code },
    }),

  /** Create an MFA challenge (login step-up) */
  challenge: (factorId: string) =>
    apiRequest<MfaChallengeResponse>("/api/auth/mfa/challenge", {
      method: "POST",
      body: { factor_id: factorId },
    }),

  /** Verify an MFA challenge to upgrade session to aal2 */
  challengeVerify: (factorId: string, challengeId: string, code: string) =>
    apiRequest<MfaVerifyResponse>("/api/auth/mfa/challenge/verify", {
      method: "POST",
      body: { factor_id: factorId, challenge_id: challengeId, code },
    }),

  /** Remove a TOTP factor (disable 2FA) */
  unenroll: (factorId: string) =>
    apiRequest<{ success: boolean; message: string }>("/api/auth/mfa/unenroll", {
      method: "DELETE",
      body: { factor_id: factorId },
    }),
};

// ── Enterprise Request API (public endpoint) ─────────────────────
export const enterpriseApi = {
  submit: (data: EnterpriseRequestCreate) =>
    apiRequest<{ status: string; id: string }>("/api/admin/request", {
      method: "POST",
      body: data,
      skipOrgContext: true,
    }),
};


// ── Types ────────────────────────────────────────────────────────

export interface Idea {
  id: string;
  user_id: string;
  organization_id?: string;
  title: string;
  description: string;
  industry?: string;
  target_market?: string;
  problem_statement?: string;
  proposed_solution?: string;
  status: string;
  current_phase?: string;
  progress: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface IdeaCreate {
  title: string;
  description: string;
  industry?: string;
  target_market?: string;
  problem_statement?: string;
  proposed_solution?: string;
}

export interface AgentActivity {
  id: string;
  idea_id: string;
  agent_name: string;
  agent_role: string;
  action: string;
  status: string;
  output_data?: Record<string, unknown>;
  duration_ms?: number;
  started_at: string;
  completed_at?: string;
}

export interface AgentRole {
  id: string;
  name: string;
  description: string;
}

export interface WorkflowState {
  id: string;
  idea_id: string;
  graph_state: Record<string, unknown>;
  current_node: string;
  iteration: number;
  quality_score?: number;
  decision_log: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowGraph {
  nodes: { id: string; label: string; type: string; description: string }[];
  edges: { from: string; to: string; label: string; type?: string }[];
  current_node?: string;
}

export interface Report {
  id: string;
  idea_id: string;
  report_type: string;
  title: string;
  content: Record<string, unknown>;
  file_url?: string;
  version: number;
  created_at: string;
}

export interface Simulation {
  id: string;
  idea_id: string;
  simulation_type: string;
  investor_profiles: Record<string, unknown>[];
  transcript: { speaker: string; role: string; content: string; timestamp: string }[];
  outcome?: string;
  funding_offered?: number;
  valuation?: number;
  feedback?: Record<string, unknown>;
  started_at: string;
  completed_at?: string;
}

export interface UsageSummary {
  total_events: number;
  total_tokens: number;
  total_cost_usd: number;
  events_by_type: Record<string, number>;
  daily_usage: { date: string; events: number; tokens: number; cost: number }[];
  period_days: number;
}

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  body?: string;
  notification_type: string;
  is_read: boolean;
  action_url?: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface UserSettings {
  user_id: string;
  llm_provider: string;
  llm_model: string;
  max_iterations: number;
  quality_threshold: number;
  notification_email: boolean;
  notification_in_app: boolean;
  webhook_url?: string;
  theme: string;
  updated_at?: string;
}

export interface ComparisonResult {
  ideas: { id: string; title: string; industry?: string; status: string; progress: number }[];
  dimensions: {
    dimension: string;
    label: string;
    scores: Record<string, number>;
  }[];
  recommendation?: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url?: string;
  plan: string;
  owner_id?: string;
  max_members: number;
  max_ideas: number;
  member_count?: number;
  parent_id?: string | null;
  my_role?: string;
  is_owner?: boolean;
  subscription_status?: string;
  created_at: string;
}

export interface OrgMember {
  id: string;
  user_id: string;
  role: string;
  full_name?: string;
  avatar_url?: string;
  joined_at: string;
}

export interface RoleInfo {
  id: string;
  label: string;
  level: number;
  description: string;
}

export interface AuditEntry {
  id: string;
  user_id: string;
  organization_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details: Record<string, unknown>;
  ip_address?: string;
  created_at: string;
}

export interface BillingPlan {
  tier: string;
  name: string;
  price: number;
  features: string[];
}

export interface BillingStatus {
  tier: string;
  status: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
}

export interface PlatformUser {
  id: string;
  full_name?: string;
  role: string;
  platform_role: string;
  tier: string;
  credits: number;
  created_at: string;
}

export interface EnterpriseRequest {
  id: string;
  company_name: string;
  contact_name: string;
  contact_email: string;
  team_size?: string;
  industry?: string;
  use_case?: string;
  required_seats?: number;
  status: string;
  created_at: string;
}

export interface EnterpriseRequestCreate {
  company_name: string;
  contact_name: string;
  contact_email: string;
  team_size?: string;
  industry?: string;
  use_case?: string;
  required_seats?: number;
  compliance_requirements?: string;
  white_label_needs?: boolean;
  billing_preferences?: string;
  notes?: string;
}

// ── MFA Types ────────────────────────────────────────────────────

export interface MfaFactor {
  id: string;
  friendly_name?: string;
  factor_type: string;
  status: "unverified" | "verified";
  created_at: string;
  updated_at: string;
}

export interface MfaFactorsResponse {
  factors: MfaFactor[];
  has_verified_factor: boolean;
  mfa_enabled: boolean;
}

export interface MfaStatusResponse {
  mfa_active: boolean;
  platform_role: string;
  org_role?: string;
  mfa_required: boolean;
  enforcement: Record<string, string>;
}

export interface MfaEnrollResponse {
  factor_id: string;
  totp: {
    qr_code: string;
    secret: string;
    uri: string;
  };
  friendly_name: string;
}

export interface MfaChallengeResponse {
  challenge_id: string;
  factor_id: string;
  expires_at?: string;
}

export interface MfaVerifyResponse {
  success: boolean;
  message?: string;
  access_token?: string;
  refresh_token?: string;
}
