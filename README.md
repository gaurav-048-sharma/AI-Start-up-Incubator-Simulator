# 🚀 AI Start-up Incubator Simulator

A full-stack AI-powered startup accelerator where autonomous agents research, validate, and pitch your startup ideas.

## Architecture

```
Frontend (Next.js 16)  ←→  Backend (FastAPI/Python)  ←→  Supabase (PostgreSQL)
     ↕                          ↕
  Supabase Auth          CrewAI + LangGraph + AutoGen
  Supabase Realtime      OpenAI / Anthropic
```

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.12+
- OpenAI API key

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
│       └── services/  # LLM + Storage services
├── supabase/          # Database migrations
└── docker-compose.yml # Local dev orchestration
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

## Tech Stack

- **Frontend**: Next.js 16, TypeScript, CSS Modules
- **Backend**: FastAPI, Python 3.12
- **AI**: CrewAI, LangGraph, AutoGen, OpenAI/Anthropic
- **Database**: Supabase (PostgreSQL + Auth + Realtime + Storage)
- **Deployment**: Vercel (frontend) + Railway (backend)
