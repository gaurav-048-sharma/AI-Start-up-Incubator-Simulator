# ═══════════════════════════════════════════════════════════════
# Terraform — AI Start-up Incubator Infrastructure
# Targets: Vercel (frontend) + Railway (backend) + Supabase (DB)
# ═══════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.5"
  required_providers {
    vercel = {
      source  = "vercel/vercel"
      version = "~> 1.0"
    }
  }

  backend "local" {
    path = "terraform.tfstate"
  }
}

# ── Variables ────────────────────────────────────────────────────
variable "vercel_api_token" {
  type        = string
  sensitive   = true
  description = "Vercel API token for deployments"
}

variable "project_name" {
  type    = string
  default = "ai-incubator"
}

variable "supabase_url" {
  type      = string
  sensitive = true
}

variable "supabase_anon_key" {
  type      = string
  sensitive = true
}

variable "backend_url" {
  type    = string
  default = "https://api.yourdomain.com"
}

# ── Vercel Frontend ─────────────────────────────────────────────
provider "vercel" {
  api_token = var.vercel_api_token
}

resource "vercel_project" "frontend" {
  name      = "${var.project_name}-frontend"
  framework = "nextjs"

  git_repository {
    type = "github"
    repo = "your-org/ai-incubator"
  }

  root_directory = "frontend"

  environment {
    key    = "NEXT_PUBLIC_SUPABASE_URL"
    value  = var.supabase_url
    target = ["production", "preview"]
  }

  environment {
    key    = "NEXT_PUBLIC_SUPABASE_ANON_KEY"
    value  = var.supabase_anon_key
    target = ["production", "preview"]
  }

  environment {
    key    = "NEXT_PUBLIC_API_URL"
    value  = var.backend_url
    target = ["production", "preview"]
  }
}

# ── Outputs ──────────────────────────────────────────────────────
output "frontend_url" {
  value = "https://${var.project_name}-frontend.vercel.app"
}
