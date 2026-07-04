import asyncio
import sys
import os

# Setup sys path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.workflows.graph import run_incubation_workflow
import structlog

async def test_workflow():
    idea = {
        "id": "test-123",
        "title": "Test Idea",
        "description": "A great idea",
        "industry": "Tech",
        "target_market": "Everyone",
        "problem_statement": "Problem",
        "proposed_solution": "Solution",
        "organization_id": "demo-org"
    }
    user_id = "test-user"
    
    print("Starting workflow...")
    try:
        final_state = await run_incubation_workflow(idea, user_id)
        print("Final State Keys:", final_state.keys())
        print("Status:", final_state.get("status"))
        print("Progress:", final_state.get("progress"))
    except Exception as e:
        print(f"Workflow crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_workflow())
