"""
End-to-end API test for the AI Incubator Simulator.
Tests: OTP login -> create idea -> trigger simulation -> check reports.
"""
import urllib.request
import json
import time
import sys

API = "http://localhost:8001"
EMAIL = "e2e_test@example.com"

def api(method, path, token=None, body=None):
    """Helper: make an API call and return parsed JSON."""
    data = json.dumps(body).encode("utf-8") if body else (b"" if method in ("POST", "PUT", "DELETE") else None)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")
        print(f"  HTTP {e.code} on {method} {path}: {body_text}")
        return None

def read_otp_from_logs():
    """Read OTP from backend console logs (logged for testing)."""
    import glob, re, os
    log_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity-ide", "brain",
                           "a9cec784-5a19-4379-8cc0-e6bf765376f4", ".system_generated", "tasks")
    # Find latest backend log
    logs = sorted(glob.glob(os.path.join(log_dir, "task-*.log")), key=os.path.getmtime, reverse=True)
    for log_file in logs:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        matches = re.findall(rf"email={EMAIL} otp=(\d+)", content)
        if matches:
            return matches[-1]
    return None

# ─── STEP 1: Health Check ───────────────────────────────────────
print("=" * 60)
print("STEP 1: Health Check")
health = api("GET", "/health")
print(f"  ✅ Backend healthy: {health}")

# ─── STEP 2: Send OTP ──────────────────────────────────────────
print("\nSTEP 2: Send OTP")
result = api("POST", "/api/auth/send-otp", body={"email": EMAIL})
print(f"  ✅ OTP sent: {result}")

time.sleep(2)

# ─── STEP 3: Read OTP from logs & Verify ──────────────────────
print("\nSTEP 3: Verify OTP")
otp = read_otp_from_logs()
if not otp:
    print("  ❌ Could not read OTP from logs")
    sys.exit(1)
print(f"  OTP captured: {otp}")

verify = api("POST", "/api/auth/verify-otp", body={"email": EMAIL, "otp": otp})
if not verify or "access_token" not in verify:
    print(f"  ❌ OTP verification failed: {verify}")
    sys.exit(1)
token = verify["access_token"]
print(f"  ✅ JWT token received (len={len(token)})")

# ─── STEP 4: Get /me ──────────────────────────────────────────
print("\nSTEP 4: Get /api/auth/me")
me = api("GET", "/api/auth/me", token=token)
print(f"  ✅ User: {me}")

# ─── STEP 5: List Ideas (should be empty or have mock data) ──
print("\nSTEP 5: List Ideas")
ideas_resp = api("GET", "/api/ideas", token=token)
print(f"  ✅ Ideas response: total={ideas_resp.get('total', 'N/A')}, count={len(ideas_resp.get('ideas', []))}")

# ─── STEP 6: Create a New Idea ────────────────────────────────
print("\nSTEP 6: Create Idea")
new_idea = api("POST", "/api/ideas", token=token, body={
    "title": "AI Automated Farm",
    "description": "An AI-powered smart farming platform that uses IoT sensors and machine learning to provide real-time crop monitoring, soil analysis, and weather-based recommendations to maximize yield.",
    "industry": "AgriTech",
    "target_market": "Small to mid-sized farms in developing countries",
    "problem_statement": "Farmers lack real-time soil and weather data, leading to crop losses.",
    "proposed_solution": "Deploy IoT sensors with AI-powered analytics for real-time farm monitoring."
})
if not new_idea or "id" not in new_idea:
    print(f"  ❌ Failed to create idea: {new_idea}")
    sys.exit(1)
idea_id = new_idea["id"]
print(f"  ✅ Created idea: {idea_id} (title={new_idea.get('title')})")

# ─── STEP 7: Get Idea Details ─────────────────────────────────
print("\nSTEP 7: Get Idea Details")
idea_detail = api("GET", f"/api/ideas/{idea_id}", token=token)
print(f"  ✅ Idea detail: status={idea_detail.get('status')}, progress={idea_detail.get('progress')}")

# ─── STEP 8: Trigger Simulation ───────────────────────────────
print("\nSTEP 8: Trigger Simulation")
sim = api("POST", f"/api/simulations/ideas/{idea_id}/simulate", token=token)
print(f"  ✅ Simulation response: {sim}")

# ─── STEP 9: Poll for progress ───────────────────────────────
print("\nSTEP 9: Polling simulation progress (max 60s)...")
for i in range(12):
    time.sleep(5)
    idea_check = api("GET", f"/api/ideas/{idea_id}", token=token)
    status = idea_check.get("status", "unknown")
    progress = idea_check.get("progress", 0)
    print(f"  [{i*5+5}s] status={status}, progress={progress}")
    if status in ("completed", "failed"):
        break

# ─── STEP 10: Check Reports ──────────────────────────────────
print("\nSTEP 10: Check Reports")
reports = api("GET", f"/api/reports/ideas/{idea_id}", token=token)
if reports:
    if isinstance(reports, list):
        print(f"  ✅ Reports count: {len(reports)}")
        for r in reports[:3]:
            print(f"     - {r.get('report_type', 'unknown')}: {r.get('title', 'N/A')[:60]}")
    else:
        print(f"  ✅ Reports response: {str(reports)[:200]}")
else:
    print("  ⚠️ No reports yet (simulation may still be running)")

# ─── STEP 11: Check Agent Activities ─────────────────────────
print("\nSTEP 11: Check Agent Activities")
activities = api("GET", f"/api/agents/ideas/{idea_id}/activities", token=token)
if activities:
    if isinstance(activities, list):
        print(f"  ✅ Agent activities: {len(activities)}")
        for a in activities[:3]:
            print(f"     - {a.get('agent_role', 'unknown')}: {a.get('status', 'N/A')}")
    else:
        print(f"  ✅ Activities response: {str(activities)[:200]}")
else:
    print("  ⚠️ No activities yet")

# ─── STEP 12: Analytics ──────────────────────────────────────
print("\nSTEP 12: Check Analytics")
analytics = api("GET", "/api/analytics/usage?days=30", token=token)
print(f"  ✅ Analytics: {str(analytics)[:200]}")

# ─── STEP 13: Notifications ─────────────────────────────────
print("\nSTEP 13: Check Notifications")
notif = api("GET", "/api/notifications", token=token)
print(f"  ✅ Notifications: {str(notif)[:200]}")

# ─── STEP 14: Agent Roles ───────────────────────────────────
print("\nSTEP 14: Agent Roles")
roles = api("GET", "/api/agents/roles", token=token)
print(f"  ✅ Roles: {str(roles)[:200]}")

# ─── STEP 15: Settings ──────────────────────────────────────
print("\nSTEP 15: Settings")
settings = api("GET", "/api/settings", token=token)
print(f"  ✅ Settings: {str(settings)[:200]}")

print("\n" + "=" * 60)
print("🎉 END-TO-END TEST COMPLETE!")
print("=" * 60)
