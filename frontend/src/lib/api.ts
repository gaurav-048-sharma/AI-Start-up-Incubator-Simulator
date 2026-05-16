const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

async function apiRequest<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const config: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };

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
