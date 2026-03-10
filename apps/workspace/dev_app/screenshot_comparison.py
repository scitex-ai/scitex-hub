#!/usr/bin/env python3
"""
Screenshot comparison script for GitHub vs Local SciTeX
Takes screenshots of specified pages and saves them for comparison
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Define screenshot pairs
SCREENSHOT_PAIRS = [
    {
        "name": "root",
        "github": "https://github.com/SciTeX-AI/scitex-cloud",
        "local": "http://127.0.0.1:8000/ywatanabe/test7/",
    },
    {
        "name": "child_directory",
        "github": "https://github.com/SciTeX-AI/scitex-cloud/tree/develop/apps",
        "local": "http://127.0.0.1:8000/ywatanabe/test7/scitex/",
    },
    {
        "name": "file_view",
        "github": "https://github.com/SciTeX-AI/scitex-cloud/blob/develop/apps/auth_app/urls.py",
        "local": "http://127.0.0.1:8000/ywatanabe/test7/blob/scitex/writer/scripts/examples/link_project_assets.sh",
    },
]

# Local credentials
LOCAL_USERNAME = "test-user"
LOCAL_PASSWORD = "test"

# Output directory
OUTPUT_DIR = Path("/home/ywatanabe/proj/scitex-cloud/apps/dev_app/screenshots")


async def take_screenshots():
    """Take screenshots of all specified pages"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)

        for pair in SCREENSHOT_PAIRS:
            print(f"\n=== Processing {pair['name']} ===")

            # GitHub screenshot
            print(f"Taking GitHub screenshot: {pair['github']}")
            github_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            github_page = await github_context.new_page()

            try:
                await github_page.goto(
                    pair["github"], wait_until="networkidle", timeout=30000
                )
                await github_page.wait_for_timeout(2000)  # Wait for animations
                github_screenshot_path = OUTPUT_DIR / f"{pair['name']}_github.png"
                await github_page.screenshot(
                    path=str(github_screenshot_path), full_page=True
                )
                print(f"  Saved: {github_screenshot_path}")
            except Exception as e:
                print(f"  Error taking GitHub screenshot: {e}")
            finally:
                await github_context.close()

            # Local screenshot (with login)
            print(f"Taking local screenshot: {pair['local']}")
            local_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            local_page = await local_context.new_page()

            try:
                # First, try to access the page
                response = await local_page.goto(
                    pair["local"], wait_until="domcontentloaded", timeout=30000
                )

                # Check if we're redirected to login
                current_url = local_page.url
                if "/login" in current_url or response.status == 401:
                    print("  Login required, attempting login...")

                    # Fill login form
                    await local_page.wait_for_selector(
                        'input[name="username"]', timeout=5000
                    )
                    await local_page.fill('input[name="username"]', LOCAL_USERNAME)
                    await local_page.fill('input[name="password"]', LOCAL_PASSWORD)

                    # Submit form
                    await local_page.click('button[type="submit"]')

                    # Wait for navigation
                    await local_page.wait_for_load_state("networkidle", timeout=10000)

                    # Navigate to the target page again
                    await local_page.goto(
                        pair["local"], wait_until="networkidle", timeout=30000
                    )

                await local_page.wait_for_timeout(2000)  # Wait for animations
                local_screenshot_path = OUTPUT_DIR / f"{pair['name']}_local.png"
                await local_page.screenshot(
                    path=str(local_screenshot_path), full_page=True
                )
                print(f"  Saved: {local_screenshot_path}")

                # Also capture the page title and URL for comparison
                title = await local_page.title()
                print(f"  Page title: {title}")
                print(f"  Final URL: {local_page.url}")

            except Exception as e:
                print(f"  Error taking local screenshot: {e}")
                # Take screenshot anyway to see what's happening
                try:
                    error_screenshot_path = (
                        OUTPUT_DIR / f"{pair['name']}_local_error.png"
                    )
                    await local_page.screenshot(
                        path=str(error_screenshot_path), full_page=True
                    )
                    print(f"  Error screenshot saved: {error_screenshot_path}")
                except:
                    pass
            finally:
                await local_context.close()

        await browser.close()
        print(f"\n=== All screenshots saved to {OUTPUT_DIR} ===")


async def main():
    """Main function"""
    print("Starting screenshot comparison...")
    print(f"Output directory: {OUTPUT_DIR}")
    await take_screenshots()


if __name__ == "__main__":
    asyncio.run(main())
