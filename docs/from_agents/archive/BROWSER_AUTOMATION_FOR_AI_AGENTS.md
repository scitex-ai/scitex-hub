# Browser Automation for AI Agents
**Date:** 2025-10-19
**Goal:** Enable AI agents to interact with SciTeX Cloud with persistent login sessions

## Problem

Currently, `scitex.capture` screenshots show login pages because:
- Playwright browser starts fresh each time (no cookies)
- No session persistence between captures
- Can't access authenticated pages

## Solution: scitex.browser + scitex.capture Integration

### Components Available

1. **scitex.browser** - Full Playwright automation
   - `automation/CookieHandler.py` - Cookie management
   - `interaction/` - Click, fill, navigation
   - `debugging/browser_logger` - Visual debugging with screenshots

2. **scitex.capture** - Screenshot capture
   - Already captures URLs via Playwright
   - Saves to `$SCITEX_DIR/capture`

### Implementation Strategy

#### Option 1: Cookie Persistence (Recommended)

```python
from playwright.async_api import async_playwright
from scitex.browser.automation import CookieHandler
from scitex import capture

async def capture_authenticated_page(url, cookie_file="~/.scitex/browser/cookies.json"):
    """
    Capture screenshot with persistent cookies.

    For AI agents to access authenticated pages.
    """
    async with async_playwright() as p:
        # Launch with persistent context
        browser = await p.chromium.launch(headless=True)

        # Load saved cookies if they exist
        context = await browser.new_context()
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)

        page = await context.new_page()
        await page.goto(url)

        # Take screenshot
        screenshot_path = f"~/.scitex/capture/{timestamp}-{url_slug}.jpg"
        await page.screenshot(path=screenshot_path, quality=90)

        # Save cookies for next time
        cookies = await context.cookies()
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f)

        await browser.close()
        return screenshot_path
```

#### Option 2: User Data Directory (Chrome Profile)

```python
async def capture_with_chrome_profile(url):
    """
    Use existing Chrome profile with all cookies/sessions.
    """
    async with async_playwright() as p:
        # Use your actual Chrome profile
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="~/.config/google-chrome/Default",
            headless=False,  # Must be False for persistent context
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(url)
        await page.screenshot(path=f"~/.scitex/capture/{timestamp}.jpg")

        await browser.close()
```

#### Option 3: Login Automation (One-time Setup)

```python
from scitex.browser.interaction import fill_with_fallbacks_async, click_with_fallbacks_async
from scitex.browser.automation import CookieHandler

async def login_and_capture(url, username, password):
    """
    Automated login flow for AI agents.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # 1. Go to login page
        await page.goto("http://127.0.0.1:8000/auth/login/")

        # 2. Fill credentials
        await fill_with_fallbacks_async(page, "#id_username", username)
        await fill_with_fallbacks_async(page, "#id_password", password)

        # 3. Click login
        await click_with_fallbacks_async(page, "button[type='submit']", "Log In")

        # 4. Wait for redirect
        await page.wait_for_url("**/core/**", timeout=5000)

        # 5. Save cookies
        cookies = await context.cookies()
        with open("~/.scitex/browser/scitex_cloud_cookies.json", 'w') as f:
            json.dump(cookies, f)

        # 6. Now navigate to actual page
        await page.goto(url)
        await page.screenshot(path=f"~/.scitex/capture/{timestamp}.jpg")

        await browser.close()
```

### Recommended Approach for AI Agents

**Hybrid: Cookie File + Auto-Login**

1. **First run:** AI agent performs automated login, saves cookies
2. **Subsequent runs:** Reuse cookies
3. **Cookie expiry:** Auto-detect login page, re-login automatically

```python
class AuthenticatedCapture:
    """
    Smart screenshot capture that maintains authentication.
    """

    def __init__(self, cookie_file="~/.scitex/browser/scitex_cloud_cookies.json"):
        self.cookie_file = cookie_file
        self.credentials = {
            'username': os.getenv('SCITEX_CLOUD_USERNAME'),
            'password': os.getenv('SCITEX_CLOUD_PASSWORD'),
        }

    async def capture(self, url):
        """Capture with auto-authentication."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            # Try to use saved cookies
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, 'r') as f:
                    cookies = json.load(f)
                    await context.add_cookies(cookies)

            page = await context.new_page()
            await page.goto(url)

            # Check if redirected to login
            if "login" in page.url.lower():
                print("Session expired, re-authenticating...")
                await self._login(page)
                await page.goto(url)  # Try again after login

            # Take screenshot
            screenshot_path = f"~/.scitex/capture/{timestamp}.jpg"
            await page.screenshot(path=screenshot_path, quality=90)

            # Update cookies
            cookies = await context.cookies()
            with open(self.cookie_file, 'w') as f:
                json.dump(cookies, f)

            await browser.close()
            return screenshot_path

    async def _login(self, page):
        """Perform login."""
        await page.goto("http://127.0.0.1:8000/auth/login/")
        await fill_with_fallbacks_async(page, "#id_username", self.credentials['username'])
        await fill_with_fallbacks_async(page, "#id_password", self.credentials['password'])
        await click_with_fallbacks_async(page, "button[type='submit']", "Log In")
        await page.wait_for_url("**/core/**", timeout=5000)
```

### Integration with scitex.capture

Update `scitex.capture.utils.snap()` to support authentication:

```python
# In utils.py
def snap(
    url=None,
    authenticated=False,  # NEW parameter
    cookie_file=None,     # NEW parameter
    **kwargs
):
    """
    Capture screenshot, optionally with authentication.

    Parameters
    ----------
    authenticated : bool
        If True, use saved cookies for authentication
    cookie_file : str
        Path to cookie file (default: ~/.scitex/browser/scitex_cloud_cookies.json)
    """
    if authenticated and url:
        # Use authenticated capture
        return asyncio.run(_capture_authenticated(url, cookie_file))
    else:
        # Use existing logic
        return _capture_url(url, **kwargs)
```

### Environment Variables

```bash
# Add to .env
SCITEX_CLOUD_USERNAME=your_username
SCITEX_CLOUD_PASSWORD=your_password
SCITEX_BROWSER_COOKIE_FILE=~/.scitex/browser/scitex_cloud_cookies.json
```

### MCP Tool Update

```python
# In mcp_server.py
async def capture_screenshot(
    self,
    url=None,
    authenticated=False,  # NEW
    **kwargs
):
    """
    Capture screenshot with optional authentication.

    For AI agents to access protected pages.
    """
    if authenticated:
        return await self._capture_authenticated(url, **kwargs)
    else:
        return await self._capture_regular(url, **kwargs)
```

### Usage for AI Agents

```python
# First time: Login and save cookies
from scitex import capture

capture.snap(
    url="127.0.0.1:8000/new/",
    authenticated=True,
    credentials={'username': 'user', 'password': 'pass'}
)

# Subsequent times: Use saved cookies
capture.snap(
    url="127.0.0.1:8000/new/",
    authenticated=True
)

# Via MCP
mcp__scitex-capture__capture_screenshot(
    url="127.0.0.1:8000/new/",
    authenticated=True
)
```

## Benefits

1. **Persistent Sessions:** AI agents maintain login state
2. **Auto-Recovery:** Automatically re-login on session expiry
3. **Security:** Credentials stored in environment variables
4. **Flexibility:** Works with any authentication system
5. **Visual Debugging:** `browser_logger` creates timeline of actions

## Implementation Steps

1. ✅ You already have `scitex.browser` with all needed components
2. ✅ You already have `scitex.capture` working
3. ⏳ Add cookie persistence to capture module
4. ⏳ Add `authenticated` parameter to `snap()` function
5. ⏳ Update MCP tools to support authentication
6. ⏳ Document for AI agents

## Security Considerations

- **Cookie Storage:** Encrypted or file permissions 600
- **Credential Storage:** Environment variables only, never hardcoded
- **Session Timeout:** Handle gracefully with auto-relogin
- **Multi-user:** Separate cookie files per user

## Example Workflow

```python
# AI Agent workflow
from scitex import capture, browser

# 1. Initial setup (one time)
await browser.login_and_save_cookies(
    url="http://127.0.0.1:8000",
    username=os.getenv("SCITEX_USERNAME"),
    password=os.getenv("SCITEX_PASSWORD"),
)

# 2. Use authenticated capture
screenshot = capture.snap(
    url="127.0.0.1:8000/new/",
    authenticated=True,
)

# 3. AI analyzes screenshot
# 4. AI interacts with page via browser automation
# 5. AI captures result
```

---

**Status:** Feasible with existing components
**Effort:** Medium (2-3 hours implementation)
**Value:** High - enables full AI agent automation
