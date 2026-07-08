# 🚀 AI Start-up Incubator Simulator

A full-stack AI-powered startup accelerator where autonomous agents research, validate, and pitch your startup ideas.
This project is an AI Venture Operating System—a SaaS platform that acts like an AI-powered startup accelerator or virtual co-founder. Users submit a startup or business idea, and the system uses specialized AI agents to automatically perform market research, competitor analysis, technical architecture planning, financial forecasting, legal checks, growth strategy creation, and investor pitch simulations. Instead of founders needing separate consultants, analysts, advisors, and strategists, this platform centralizes the entire startup validation and planning process into one intelligent system.


## Architecture

```
Frontend (Next.js 16)  <-->  Backend (FastAPI/Python)  <-->  SQLite Database
     |                           | 
  Custom Auth            CrewAI + LangGraph + AutoGen
  WebSockets             Gemini / Anthropic
```

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.12+
- Gemini API key

### 1. Clone and configure
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start the backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

### 4. Open the app
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs (debug mode)

## Features

### Core Platform
- **5 AI Research Agents** — Market Analyst, Tech Architect, Growth Strategist, Financial Analyst, Legal Advisor
- **LangGraph Workflow Engine** — 6-node state machine with quality gates and retry loops
- **Investor Pitch Simulation** — Multi-round AI investor personas with funding verdicts
- **Real-time Updates** — WebSocket-powered live agent activity and workflow tracking

### Dashboard
- **Overview** — Stats, quick actions, service health, recent ideas
- **Ideas CRUD** — Submit, track, and manage startup ideas
- **Agent Monitor** — Real-time agent activity tracking
- **Workflow Visualizer** — Interactive graph with live progress
- **Reports** — View and explore AI-generated analysis reports
- **Compare Ideas** — Side-by-side multi-dimension comparison with radar charts
- **Settings** — LLM provider selection, notification preferences, webhook config

### Enterprise Features
- **Analytics & Usage Tracking** — Token usage, cost reporting, credit management
- **In-App Notifications** — Workflow/simulation completion alerts with bell dropdown
- **Webhook Integration** — Slack/Discord/custom webhooks on workflow events
- **Stripe Billing** — Free, Pro, Enterprise tiers with feature gating
- **RBAC & Feature Flags** — Tier-based access control per feature
- **Security Middleware** — Rate limiting, JWT auth, request tracing

### Recommended Admin Hierarchy
- **Platform Super Admin** — Manages database migrations, global feature flags, suspends malicious organizations
- **Platform Support** — Read-only global visibility for troubleshooting
- **Workspace Owner** — Pays the bill and holds financial liability for the workspace
- **Incubator Manager / Org Admin** — Manages users, sets up SSO, accesses all workflows inside the isolated org
- **Members / Founders** — Read/write access scoped to their project bounds

## Project Structure

```
├── frontend/          # Next.js 16 (TypeScript, CSS Modules)
│   └── src/app/       # App Router pages
├── backend/           # FastAPI + Python AI Engine
│   └── app/
│       ├── agents/    # CrewAI agent definitions
│       ├── workflows/ # LangGraph state machine
│       ├── simulation/# AutoGen investor pitch
│       ├── api/       # REST + WebSocket routes
│       ├── tools/     # Search, financial, code tools
│       ├── models/    # Pydantic schemas + DB client
│       └── services/  # LLM, Analytics, Notifications
├── docker-compose.yml # Local dev orchestration
```

## AI Agents

| Agent | Role | Output |
|-------|------|--------|
| 🔬 Market Analyst | TAM/SAM/SOM, competitors, trends | Market Research Report |
| 🏗️ Tech Architect | Stack, architecture, MVP spec | Technical Blueprint |
| 🚀 Growth Strategist | GTM, pricing, acquisition | Growth Strategy |
| 💹 Financial Analyst | Revenue, unit economics, funding | Financial Model |
| ⚖️ Legal Advisor | IP, compliance, corporate | Legal Review |

## Workflow

```
Research → Quality Gate → Plan → Build → Simulate → Complete
   ↑                |
   └── retry ←──────┘  (if quality < 0.7)
```

## API Endpoints

| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| Ideas | `/api/ideas` | CRUD, launch workflow, compare |
| Agents | `/api/agents` | Roles, activity logs |
| Workflows | `/api/workflows` | Graph structure, state tracking |
| Reports | `/api/reports` | List, view, export |
| Simulations | `/api/simulations` | Start pitch, view results |
| Analytics | `/api/analytics` | Usage summary, credits, cost |
| Notifications | `/api/notifications` | List, unread count, mark read |
| Settings | `/api/settings` | Get/update user preferences |
| Billing | `/api/billing` | Plans, checkout, webhooks |

## Tech Stack

- **Frontend**: Next.js 16, TypeScript, CSS Modules (Glassmorphism design system)
- **Backend**: FastAPI, Python 3.12, Pydantic v2
- **AI**: CrewAI, LangGraph, AutoGen, Gemini/Anthropic
- **Database**: SQLite (Local)
- **Infrastructure**: Docker Compose, Redis, Prometheus, Grafana
- **Deployment**: Vercel (frontend) + Railway (backend)
