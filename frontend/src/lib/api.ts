const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

export async function apiRequest<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const config: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };

  // Try to inject Supabase JWT if client is available
  if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SUPABASE_URL) {
    try {
      const { createClient } = await import("./supabase/client");
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      if (data?.session?.access_token) {
        (config.headers as Record<string, string>)["Authorization"] = `Bearer ${data.session.access_token}`;
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

// ── Organizations API ────────────────────────────────────────────
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

// ── Types ────────────────────────────────────────────────────────
export interface Idea {
  id: string;
  user_id: string;
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
  my_role?: string;
  is_owner?: boolean;
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
