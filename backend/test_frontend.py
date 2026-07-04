import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to frontend dashboard...")
        await page.goto("http://localhost:3000/dashboard/ideas/new", timeout=15000)
        
        print("Taking initial screenshot...")
        # Get artifact directory from environment or hardcode
        artifact_dir = r"C:\Users\rohan\.gemini\antigravity-ide\brain\a9cec784-5a19-4379-8cc0-e6bf765376f4"
        await page.screenshot(path=os.path.join(artifact_dir, "frontend_step1.png"))
        
        print("Clicking 'Fill with Dummy Data'...")
        await page.click("button:has-text('Fill with Dummy Data')")
        
        print("Clicking 'Next: Problem & Solution'...")
        await page.click("button:has-text('Next: Problem & Solution')")
        await page.screenshot(path=os.path.join(artifact_dir, "frontend_step2.png"))
        
        print("Clicking 'Review & Launch'...")
        await page.click("button:has-text('Review & Launch')")
        await page.screenshot(path=os.path.join(artifact_dir, "frontend_step3.png"))
        
        print("Clicking 'Launch Incubation'...")
        await page.click("button:has-text('Launch Incubation')")
        
        print("Waiting for launch to complete (could take some time depending on mock db latency)...")
        # Wait for the redirection to the idea detail page
        await page.wait_for_url(r"**/dashboard/ideas/*", timeout=20000)
        
        print("Taking final screenshot of Idea Detail page...")
        await page.screenshot(path=os.path.join(artifact_dir, "frontend_final.png"), full_page=True)
        
        print("Test completed successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
