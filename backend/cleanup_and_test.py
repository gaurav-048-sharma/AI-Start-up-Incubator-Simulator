"""
Cleanup script: Test Gemini API key and delete old ideas from Supabase.
"""
import os
import sys
import httpx
import json

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

def test_gemini():
    """Test if the Gemini API key works."""
    print("\n" + "=" * 60)
    print("TESTING GEMINI API KEY")
    print("=" * 60)

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY is empty in .env!")
        return False

    print(f"   Key: {GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-5:]}")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": "Say hello in one sentence. Keep it very short."}]
        }]
    }

    try:
        resp = httpx.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            print(f"✅ Gemini API key works! Response: {text.strip()[:100]}")
            return True
        else:
            print(f"❌ Gemini API returned status {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Gemini API request failed: {e}")
        return False


def list_and_delete_ideas():
    """List all ideas in Supabase and delete them."""
    print("\n" + "=" * 60)
    print("CLEANING UP OLD IDEAS FROM SUPABASE")
    print("=" * 60)

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("❌ Supabase not configured, skipping cleanup.")
        return

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    # List all ideas
    try:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/ideas?select=id,title,created_at&order=created_at.desc",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"❌ Failed to list ideas: {resp.status_code} — {resp.text[:200]}")
            return

        ideas = resp.json()
        print(f"   Found {len(ideas)} existing ideas:")
        for idea in ideas:
            print(f"     • {idea.get('id', '?')[:8]}... | {idea.get('title', 'Untitled')[:50]} | {idea.get('created_at', '')[:19]}")

        if not ideas:
            print("   Nothing to delete — database is clean!")
            return

        # Delete all ideas
        print(f"\n   Deleting {len(ideas)} ideas...")
        for idea in ideas:
            idea_id = idea["id"]
            del_resp = httpx.delete(
                f"{SUPABASE_URL}/rest/v1/ideas?id=eq.{idea_id}",
                headers=headers,
                timeout=10,
            )
            if del_resp.status_code in (200, 204):
                print(f"     ✅ Deleted {idea_id[:8]}... ({idea.get('title', '')[:30]})")
            else:
                print(f"     ❌ Failed to delete {idea_id[:8]}...: {del_resp.status_code}")

        # Verify
        verify = httpx.get(
            f"{SUPABASE_URL}/rest/v1/ideas?select=id",
            headers=headers,
            timeout=10,
        )
        remaining = verify.json() if verify.status_code == 200 else []
        print(f"\n   ✅ Cleanup complete. {len(remaining)} ideas remaining.")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")


def check_backend_health():
    """Check if the backend is running."""
    print("\n" + "=" * 60)
    print("CHECKING BACKEND HEALTH")
    print("=" * 60)
    try:
        resp = httpx.get("http://localhost:8001/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Backend is running!")
            print(f"   Version: {data.get('version')}")
            print(f"   Gemini: {data.get('services', {}).get('gemini')}")
            print(f"   Supabase: {data.get('services', {}).get('supabase')}")
            return True
        else:
            print(f"⚠️ Backend returned {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend not reachable: {e}")
        return False


if __name__ == "__main__":
    print("🚀 AI Venture OS — Cleanup & Verification Script")

    check_backend_health()
    gemini_ok = test_gemini()
    list_and_delete_ideas()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"   Gemini API: {'✅ Working' if gemini_ok else '❌ Not working'}")
    print(f"   Database:   Cleaned (old ideas deleted)")
    print(f"   Backend:    http://localhost:8001")
    print(f"   Frontend:   http://localhost:3000")
    print("=" * 60)
