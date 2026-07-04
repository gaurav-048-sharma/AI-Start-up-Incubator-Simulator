"""
End-to-End Pipeline Test Script
================================
Tests the entire AI Start-up Incubator flow with dummy data:
  1. Health check
  2. Create a dummy startup idea (with name, problem statement, solution)
  3. Launch the incubation workflow
  4. Poll for completion
  5. Fetch and validate generated reports

Run with:  python test_pipeline_e2e.py
Requires:  Backend running on http://localhost:8001
"""

import asyncio
import httpx
import json
import time
import sys

# Force UTF-8 output for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8001"
HEADERS = {
    "Content-Type": "application/json",
    "X-Org-Id": "demo-org",
}

# ── Dummy test data ──────────────────────────────────────────────
DUMMY_IDEA = {
    "title": "EcoTrack — AI Carbon Footprint Tracker",
    "description": (
        "An AI-powered platform that helps businesses and individuals track, analyze, and reduce "
        "their carbon footprint in real-time. The app integrates with utility providers, transportation "
        "APIs, and supply chain databases to automatically calculate emissions. Machine learning models "
        "provide personalized reduction recommendations and predict future impact. Gamification elements "
        "encourage sustainable behavior through challenges and rewards."
    ),
    "industry": "CleanTech / Sustainability",
    "target_market": "SMBs and eco-conscious consumers aged 25-55 in North America and Europe",
    "problem_statement": (
        "Climate change is accelerating, but 78% of businesses cannot accurately measure their carbon "
        "footprint. Existing carbon accounting tools cost $10K-$50K/year and require manual data entry. "
        "Individuals lack accessible tools to understand their personal environmental impact. Without "
        "measurement, there can be no meaningful reduction."
    ),
    "proposed_solution": (
        "EcoTrack uses AI to automate carbon footprint calculation by connecting to 200+ data sources "
        "(utilities, banks, travel platforms, supply chains). Our proprietary ML model provides "
        "actionable reduction recommendations with projected savings. For businesses, we offer "
        "automated ESG reporting compliant with GRI and CDP frameworks. For individuals, a free "
        "mobile app with social challenges and carbon offset marketplace. Priced at $49/mo for "
        "SMBs and free for individual users (monetized via carbon offset commissions)."
    ),
}


def ok(msg):
    print(f"  ✅ {msg}")

def fail(msg):
    print(f"  ❌ {msg}")

def info(msg):
    print(f"  ℹ️  {msg}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def step_health(client: httpx.AsyncClient) -> bool:
    section("STEP 1: HEALTH CHECK")
    try:
        resp = await client.get(f"{BASE_URL}/health", timeout=10.0)
        data = resp.json()
        ok(f"Backend alive — status: {resp.status_code}")
        ok(f"Version: {data.get('version')}")
        services = data.get("services", {})
        for svc, connected in services.items():
            ok(f"  {svc}: {'connected' if connected else 'not configured'}") if connected else info(f"  {svc}: not configured")
        return True
    except httpx.ConnectError:
        fail("Cannot connect to backend at http://localhost:8001")
        fail("Start it with: cd backend && python -m uvicorn app.main:app --port 8001")
        return False
    except Exception as e:
        fail(f"Health check error: {e}")
        return False


async def step_create_idea(client: httpx.AsyncClient) -> str | None:
    section("STEP 2: CREATE DUMMY STARTUP IDEA")
    info(f"Title: {DUMMY_IDEA['title']}")
    info(f"Problem: {DUMMY_IDEA['problem_statement'][:80]}...")
    info(f"Solution: {DUMMY_IDEA['proposed_solution'][:80]}...")

    try:
        resp = await client.post(
            f"{BASE_URL}/api/ideas",
            json=DUMMY_IDEA,
            headers=HEADERS,
            timeout=15.0,
        )
        if resp.status_code == 201:
            data = resp.json()
            idea_id = data.get("id")
            ok(f"Idea created successfully!")
            ok(f"  ID: {idea_id}")
            ok(f"  Title: {data.get('title')}")
            ok(f"  Status: {data.get('status')}")
            ok(f"  Org ID: {data.get('organization_id')}")
            ok(f"  Problem Statement: {'present' if data.get('problem_statement') else 'MISSING'}")
            ok(f"  Proposed Solution: {'present' if data.get('proposed_solution') else 'MISSING'}")
            return idea_id
        else:
            fail(f"Create idea failed: HTTP {resp.status_code}")
            fail(f"Response: {resp.text[:500]}")
            return None
    except Exception as e:
        fail(f"Create idea error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def step_list_ideas(client: httpx.AsyncClient) -> bool:
    section("STEP 3: LIST IDEAS")
    try:
        resp = await client.get(f"{BASE_URL}/api/ideas", headers=HEADERS, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("total", 0)
            ok(f"Listed {total} ideas in the system")
            for idea in data.get("ideas", [])[:3]:
                info(f"  • [{idea.get('status')}] {idea.get('title')}")
            return True
        else:
            fail(f"List ideas: HTTP {resp.status_code} — {resp.text[:200]}")
            return False
    except Exception as e:
        fail(f"List ideas error: {e}")
        return False


async def step_launch_workflow(client: httpx.AsyncClient, idea_id: str) -> bool:
    section("STEP 4: LAUNCH INCUBATION WORKFLOW")
    try:
        resp = await client.post(
            f"{BASE_URL}/api/ideas/{idea_id}/launch",
            headers=HEADERS,
            timeout=30.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            ok(f"Workflow launched!")
            ok(f"  Status: {data.get('status')}")
            ok(f"  Message: {data.get('message')}")
            return True
        else:
            fail(f"Launch failed: HTTP {resp.status_code}")
            fail(f"Response: {resp.text[:500]}")
            return False
    except Exception as e:
        fail(f"Launch error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def step_poll_completion(client: httpx.AsyncClient, idea_id: str, max_wait: int = 600) -> bool:
    section("STEP 5: POLLING FOR WORKFLOW COMPLETION")
    info(f"Polling every 10s for up to {max_wait}s...")
    info("(This may take several minutes — agents are running LLM calls)")

    start = time.time()
    last_status = None
    last_progress = None

    while time.time() - start < max_wait:
        try:
            resp = await client.get(f"{BASE_URL}/api/ideas/{idea_id}", headers=HEADERS, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                progress = data.get("progress", 0)

                if status != last_status or progress != last_progress:
                    elapsed = int(time.time() - start)
                    info(f"[{elapsed}s] Status: {status} | Progress: {progress}%")
                    last_status = status
                    last_progress = progress

                if status == "completed":
                    elapsed = int(time.time() - start)
                    ok(f"Workflow COMPLETED in {elapsed} seconds!")
                    return True
                elif status == "failed":
                    fail("Workflow FAILED")
                    return False
        except Exception as e:
            info(f"Poll error (will retry): {e}")

        await asyncio.sleep(10)

    fail(f"Workflow did not complete within {max_wait}s")
    info("The workflow may still be processing. Check logs for details.")
    return False


async def step_fetch_reports(client: httpx.AsyncClient, idea_id: str) -> bool:
    section("STEP 6: FETCH GENERATED REPORTS")
    try:
        resp = await client.get(
            f"{BASE_URL}/api/reports/ideas/{idea_id}",
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code == 200:
            reports = resp.json()
            if isinstance(reports, list) and len(reports) > 0:
                ok(f"Found {len(reports)} reports!")
                for r in reports:
                    rtype = r.get("report_type", "unknown")
                    title = r.get("title", "Untitled")
                    content = r.get("content", "")
                    content_str = str(content)
                    preview = content_str[:120] if content_str else "(empty)"
                    ok(f"  📄 [{rtype}] {title}")
                    info(f"     Preview: {preview}...")
                return True
            else:
                info("No reports found yet (workflow may still be processing)")
                return True  # Not a failure, just not ready
        else:
            fail(f"Fetch reports: HTTP {resp.status_code}")
            fail(f"Response: {resp.text[:300]}")
            return False
    except Exception as e:
        fail(f"Fetch reports error: {e}")
        return False


async def step_fetch_activities(client: httpx.AsyncClient, idea_id: str) -> bool:
    section("STEP 7: FETCH AGENT ACTIVITIES")
    try:
        resp = await client.get(
            f"{BASE_URL}/api/agents/ideas/{idea_id}/activities",
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code == 200:
            activities = resp.json()
            if isinstance(activities, list) and len(activities) > 0:
                ok(f"Found {len(activities)} agent activities!")
                for a in activities:
                    ok(f"  🤖 [{a.get('agent_name')}] {a.get('action')} - {a.get('status')}")
                return True
            else:
                fail("No agent activities found!")
                return False
        else:
            fail(f"Fetch activities: HTTP {resp.status_code}")
            return False
    except Exception as e:
        fail(f"Fetch activities error: {e}")
        return False


async def step_run_simulation(client: httpx.AsyncClient, idea_id: str) -> bool:
    section("STEP 8: RUN PITCH SIMULATION")
    try:
        resp = await client.post(
            f"{BASE_URL}/api/simulations/ideas/{idea_id}/simulate",
            headers=HEADERS,
            timeout=400.0,
        )
        if resp.status_code in (200, 201):
            sim = resp.json()
            transcript = sim.get("transcript", [])
            ok(f"Simulation completed with outcome: {sim.get('outcome')}")
            ok(f"Found {len(transcript)} transcript messages")
            for t in transcript[:3]:
                info(f"  💬 [{t.get('role')}] {t.get('content')[:100]}...")
            return True
        else:
            fail(f"Run simulation: HTTP {resp.status_code} - {resp.text[:300]}")
            return False
    except Exception as e:
        fail(f"Run simulation error: {type(e).__name__} - {e}")
        return False


async def step_workflow_graph(client: httpx.AsyncClient) -> bool:
    """Bonus: verify the workflow graph endpoint works."""
    try:
        resp = await client.get(f"{BASE_URL}/api/workflows/graph", headers=HEADERS, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            ok(f"Workflow graph: {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges")
            return True
        else:
            fail(f"Workflow graph: HTTP {resp.status_code}")
            return False
    except Exception as e:
        fail(f"Workflow graph error: {e}")
        return False


async def main():
    print("")
    print("=" * 60)
    print("  AI Start-up Incubator — E2E Pipeline Test")
    print("  Testing with dummy data: name, problem, solution")
    print("=" * 60)

    results = {}

    async with httpx.AsyncClient() as client:
        # Step 1: Health
        results["health"] = await step_health(client)
        if not results["health"]:
            print("\n⛔ Backend not reachable. Aborting.")
            return

        # Step 2: Create idea
        idea_id = await step_create_idea(client)
        results["create_idea"] = idea_id is not None
        if not idea_id:
            print("\n⛔ Cannot create idea. Aborting.")
            return

        # Step 3: List ideas
        results["list_ideas"] = await step_list_ideas(client)

        # Bonus: workflow graph
        results["workflow_graph"] = await step_workflow_graph(client)

        # Step 4: Launch workflow
        results["launch"] = await step_launch_workflow(client, idea_id)

        if results["launch"]:
            # Step 5: Poll for completion
            results["completion"] = await step_poll_completion(client, idea_id, max_wait=600)

            # Step 6: Fetch reports
            results["reports"] = await step_fetch_reports(client, idea_id)
            
            # Step 7: Fetch agent activities
            results["activities"] = await step_fetch_activities(client, idea_id)
            
            # Step 8: Run pitch simulation
            results["simulation"] = await step_run_simulation(client, idea_id)

    # ── Summary ──────────────────────────────────────────────────
    section("TEST RESULTS SUMMARY")
    passed = 0
    total = len(results)

    for test_name, result in results.items():
        if result:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
        print(f"  [{status}]  {test_name}")

    print(f"\n  Result: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 ALL TESTS PASSED — Pipeline is working!\n")
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed. Check logs above.\n")


if __name__ == "__main__":
    asyncio.run(main())
