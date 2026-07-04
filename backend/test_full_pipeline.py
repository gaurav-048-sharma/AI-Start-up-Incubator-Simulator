"""
Full Pipeline Test Script
=========================
Tests the entire AI Start-up Incubator flow:
1. Health check (backend reachable)
2. NVIDIA API key validation (direct LLM calls)
3. Supabase connectivity
4. Create a dummy startup idea
5. Launch the incubation workflow
6. Poll for reports
7. Fetch generated reports

Run with: python test_full_pipeline.py
"""

import asyncio
import httpx
import json
import time
import sys
import os

# Force UTF-8 output for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = "http://localhost:8001"
HEADERS = {
    "Content-Type": "application/json",
    "X-Org-Id": "demo-org",  # Bypass auth uses demo-org
}

DUMMY_IDEA = {
    "title": "AI-Powered Personal Finance Coach",
    "description": (
        "An intelligent personal finance assistant that uses AI to analyze spending patterns, "
        "predict future expenses, provide personalized savings recommendations, and automate "
        "investment decisions. The app connects to bank accounts via Plaid, uses NLP to categorize "
        "transactions, and employs reinforcement learning to optimize investment portfolios "
        "based on individual risk tolerance and financial goals."
    ),
    "industry": "FinTech",
    "target_market": "Millennials and Gen Z professionals aged 22-40 with annual income $40K-$150K",
    "problem_statement": (
        "Most people struggle with financial planning. 65% of Americans live paycheck to paycheck. "
        "Traditional financial advisors charge $150-$300/hour, making personalized advice inaccessible "
        "to the average person. Existing budgeting apps only track spending but don't provide "
        "actionable AI-driven recommendations."
    ),
    "proposed_solution": (
        "An AI coach that acts like a $300/hour financial advisor for $9.99/month. It learns your "
        "spending habits, predicts bills, auto-negotiates subscriptions, finds optimal savings rates, "
        "and builds diversified micro-investment portfolios. The AI improves over time with each "
        "user interaction, creating a truly personalized financial experience."
    ),
}


def ok(msg):
    print(f"  [PASS] {msg}")

def fail(msg):
    print(f"  [FAIL] {msg}")

def info(msg):
    print(f"  [INFO] {msg}")

def section(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


async def test_health(client: httpx.AsyncClient) -> bool:
    """Test 1: Health check"""
    section("1. HEALTH CHECK")
    try:
        resp = await client.get(f"{BASE_URL}/health", timeout=10.0)
        data = resp.json()
        ok(f"Backend is running (status: {resp.status_code})")
        ok(f"Version: {data.get('version')}")
        ok(f"Environment: {data.get('environment')}")
        
        services = data.get("services", {})
        for svc, status in services.items():
            if status:
                ok(f"Service '{svc}': connected")
            else:
                info(f"Service '{svc}': not connected (optional)")
        
        return True
    except httpx.ConnectError:
        fail("Cannot connect to backend at http://localhost:8001")
        fail("Make sure the backend is running: cd backend && python -m uvicorn app.main:app --port 8001")
        return False
    except Exception as e:
        fail(f"Health check failed: {e}")
        return False


async def test_nvidia_api_keys() -> dict:
    """Test 2: Validate NVIDIA API keys by making direct calls"""
    section("2. NVIDIA API KEY VALIDATION")
    
    results = {}
    
    try:
        from app.config import get_settings
        settings = get_settings()
        
        keys = {
            "Key 1 (Nemotron Ultra + Llama 3.3)": (settings.nvidia_api_key_1, settings.nvidia_fast_model),
            "Key 2 (DeepSeek V4 + Qwen3)": (settings.nvidia_api_key_2, settings.nvidia_reasoning_model),
            "Key 3 (Nemotron Nano VL)": (settings.nvidia_api_key_3, settings.nvidia_vision_model),
        }
        
        for name, (key, model) in keys.items():
            if not key:
                fail(f"{name}: NOT SET")
                results[name] = False
                continue
            
            # Mask key for display
            masked = key[:10] + "..." + key[-4:]
            info(f"{name}: {masked}")
            
            # Test real LLM call
            info(f"  Testing model: {model}...")
            try:
                async with httpx.AsyncClient(timeout=30.0) as api_client:
                    test_payload = {
                        "model": model,
                        "messages": [
                            {"role": "user", "content": "Respond with exactly: API_KEY_VALID"}
                        ],
                        "max_tokens": 20,
                        "temperature": 0.0,
                    }
                    
                    resp = await api_client.post(
                        f"{settings.nvidia_base_url}/chat/completions",
                        json=test_payload,
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        ok(f"  {name} -> LLM call SUCCESS: '{content[:80]}'")
                        results[name] = True
                    else:
                        fail(f"  {name} -> LLM call FAILED: HTTP {resp.status_code}")
                        error_text = resp.text[:300]
                        fail(f"  Error: {error_text}")
                        results[name] = False
            except Exception as e:
                fail(f"  {name} -> Exception: {e}")
                results[name] = False
        
    except Exception as e:
        fail(f"API key validation error: {e}")
        import traceback
        traceback.print_exc()
    
    return results


async def test_supabase() -> bool:
    """Test 3: Validate Supabase connectivity"""
    section("3. SUPABASE CONNECTIVITY")
    
    try:
        from app.config import get_settings
        settings = get_settings()
        
        if not settings.has_supabase:
            info("Supabase not configured - running in demo mode")
            return True
        
        info(f"Supabase URL: {settings.supabase_url}")
        
        # Test connectivity by hitting the REST API
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.supabase_url}/rest/v1/",
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Authorization": f"Bearer {settings.supabase_anon_key}",
                },
            )
            if resp.status_code in (200, 401, 403):
                ok(f"Supabase API reachable (HTTP {resp.status_code})")
                
                # Try listing ideas table
                resp2 = await client.get(
                    f"{settings.supabase_url}/rest/v1/ideas?limit=1",
                    headers={
                        "apikey": settings.supabase_anon_key,
                        "Authorization": f"Bearer {settings.supabase_service_role_key}",
                    },
                )
                if resp2.status_code == 200:
                    ideas_data = resp2.json()
                    ok(f"Ideas table accessible, {len(ideas_data)} existing ideas found")
                else:
                    info(f"Ideas table query returned HTTP {resp2.status_code}: {resp2.text[:200]}")
                
                return True
            else:
                fail(f"Supabase API returned HTTP {resp.status_code}")
                return False
                
    except Exception as e:
        fail(f"Supabase test failed: {e}")
        return False


async def test_create_idea(client: httpx.AsyncClient) -> str | None:
    """Test 4: Create a dummy startup idea"""
    section("4. CREATE DUMMY STARTUP IDEA")
    
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
            ok(f"ID: {idea_id}")
            ok(f"Title: {data.get('title')}")
            ok(f"Status: {data.get('status')}")
            ok(f"Org ID: {data.get('organization_id')}")
            return idea_id
        else:
            fail(f"Failed to create idea: HTTP {resp.status_code}")
            fail(f"Response: {resp.text[:500]}")
            return None
    except Exception as e:
        fail(f"Create idea error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_list_ideas(client: httpx.AsyncClient) -> bool:
    """Test 4b: List ideas"""
    try:
        resp = await client.get(
            f"{BASE_URL}/api/ideas",
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            ok(f"Listed {data.get('total', 0)} ideas")
            return True
        else:
            fail(f"List ideas failed: HTTP {resp.status_code} - {resp.text[:200]}")
            return False
    except Exception as e:
        fail(f"List ideas error: {e}")
        return False


async def test_launch_workflow(client: httpx.AsyncClient, idea_id: str) -> bool:
    """Test 5: Launch the incubation workflow"""
    section("5. LAUNCH INCUBATION WORKFLOW")
    
    try:
        resp = await client.post(
            f"{BASE_URL}/api/ideas/{idea_id}/launch",
            headers=HEADERS,
            timeout=30.0,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            ok(f"Workflow launched!")
            ok(f"Status: {data.get('status')}")
            ok(f"Message: {data.get('message')}")
            return True
        else:
            fail(f"Launch failed: HTTP {resp.status_code}")
            fail(f"Response: {resp.text[:500]}")
            return False
    except Exception as e:
        fail(f"Launch workflow error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_poll_for_completion(client: httpx.AsyncClient, idea_id: str, max_wait: int = 300) -> bool:
    """Test 6: Poll for workflow completion"""
    section("6. POLLING FOR WORKFLOW COMPLETION")
    
    info(f"Polling every 10 seconds for up to {max_wait}s...")
    
    start_time = time.time()
    last_status = None
    last_progress = None
    
    while time.time() - start_time < max_wait:
        try:
            resp = await client.get(
                f"{BASE_URL}/api/ideas/{idea_id}",
                headers=HEADERS,
                timeout=10.0,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                progress = data.get("progress", 0)
                
                if status != last_status or progress != last_progress:
                    elapsed = int(time.time() - start_time)
                    info(f"[{elapsed}s] Status: {status} | Progress: {progress}%")
                    last_status = status
                    last_progress = progress
                
                if status == "completed":
                    elapsed = int(time.time() - start_time)
                    ok(f"Workflow COMPLETED in {elapsed} seconds!")
                    return True
                elif status == "failed":
                    fail("Workflow FAILED")
                    return False
            else:
                info(f"Poll response: HTTP {resp.status_code}")
                
        except Exception as e:
            info(f"Poll error: {e}")
        
        await asyncio.sleep(10)
    
    fail(f"Workflow did not complete within {max_wait}s")
    info("The workflow is still processing in the background.")
    info("Reports may still be generated. Check manually later.")
    return False


async def test_fetch_reports(client: httpx.AsyncClient, idea_id: str) -> bool:
    """Test 7: Fetch generated reports"""
    section("7. FETCH GENERATED REPORTS")
    
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
                    report_type = r.get("report_type", "unknown")
                    title = r.get("title", "Untitled")
                    content = r.get("content", "")
                    content_str = str(content)
                    content_preview = content_str[:100] if content_str else "(empty)"
                    ok(f"  [{report_type}] {title}")
                    info(f"    Preview: {content_preview}...")
                return True
            else:
                info("No reports found yet (workflow may still be processing)")
                return True
        else:
            fail(f"Fetch reports failed: HTTP {resp.status_code}")
            fail(f"Response: {resp.text[:300]}")
            return False
    except Exception as e:
        fail(f"Fetch reports error: {e}")
        return False


async def test_workflow_graph(client: httpx.AsyncClient) -> bool:
    """Test bonus: Get workflow graph structure"""
    try:
        resp = await client.get(
            f"{BASE_URL}/api/workflows/graph",
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            ok(f"Workflow graph: {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges")
            return True
        else:
            fail(f"Workflow graph failed: HTTP {resp.status_code}")
            return False
    except Exception as e:
        fail(f"Workflow graph error: {e}")
        return False


async def main():
    print("")
    print("=" * 60)
    print("AI Start-up Incubator -- Full Pipeline Test")
    print("=" * 60)
    
    results = {}
    
    async with httpx.AsyncClient() as client:
        # Test 1: Health
        results["health"] = await test_health(client)
        if not results["health"]:
            print("\n[ABORT] Backend not reachable. Aborting.")
            return
        
        # Test 2: NVIDIA API Keys (direct -- doesn't need backend)
        nvidia_results = await test_nvidia_api_keys()
        results["nvidia_keys"] = all(v for v in nvidia_results.values()) if nvidia_results else False
        
        # Test 3: Supabase
        results["supabase"] = await test_supabase()
        
        # Test 4: Create idea
        idea_id = await test_create_idea(client)
        results["create_idea"] = idea_id is not None
        
        if not idea_id:
            print("\n[ABORT] Cannot proceed without an idea. Aborting.")
            return
        
        # Test 4b: List ideas
        results["list_ideas"] = await test_list_ideas(client)
        
        # Test bonus: workflow graph
        results["workflow_graph"] = await test_workflow_graph(client)
        
        # Test 5: Launch workflow
        results["launch"] = await test_launch_workflow(client, idea_id)
        
        if results["launch"]:
            # Test 6: Poll for completion
            results["completion"] = await test_poll_for_completion(client, idea_id, max_wait=300)
            
            # Test 7: Fetch reports
            results["reports"] = await test_fetch_reports(client, idea_id)
    
    # Summary
    section("TEST RESULTS SUMMARY")
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        if result and result is not False:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
        print(f"  [{status}]  {test_name}")
    
    print(f"\n  Result: {passed}/{total} tests passed\n")


if __name__ == "__main__":
    asyncio.run(main())
