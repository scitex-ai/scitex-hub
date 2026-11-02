"""Native owned Chromium controls for live-count refresh (no GitHub/user traffic).

Run with the normal Hub development environment and an installed Chromium:
python .github/ci/check_landing_github_counts.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "apps/infra/public_app/static/public_app/js/landing-github-counts.js"


def main():
    """Exercise actual shipped JS with disposable public-count protocol fixtures."""
    calls = []
    values = [(7, 3), (8, 4), None, (-1, 0), (0, 0)]
    card = """<li data-github-repo="scitex-sdk"><div class="landing-oss-counts">
<a data-github-count-link data-github-label="stars" href="#stars"><span data-github-stars>1</span></a>
<a data-github-count-link data-github-label="forks" href="#forks"><span data-github-forks>2</span></a>
<span data-github-unavailable hidden>Counts unavailable</span></div></li>"""
    html = f"""<section data-github-counts-url="/api/landing/github-counts/">{card}</section>
<script type="module" src="/counts.js"></script>"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get(
                "SCITEX_TEST_CHROMIUM",
                "/home/ywatanabe/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell",
            )
        )
        page = browser.new_page()
        page.clock.install()

        def route(request):
            url = request.request.url
            if url == "http://owned.test/":
                request.fulfill(content_type="text/html", body=html)
            elif url == "http://owned.test/counts.js":
                request.fulfill(content_type="text/javascript", body=SCRIPT.read_text())
            elif url == "http://owned.test/api/landing/github-counts/":
                value = values[min(len(calls), len(values) - 1)]
                calls.append(request.request.headers)
                if value is None:
                    request.fulfill(status=503, body="unavailable")
                else:
                    payload = {
                        "status": "snapshot" if len(calls) == 5 else "fresh",
                        "fetched_at": "2026-11-03T00:00:00+00:00",
                        "repositories": {
                            "scitex-sdk": {
                                "available": True,
                                "stars": value[0],
                                "forks": value[1],
                            }
                        },
                    }
                    request.fulfill(
                        content_type="application/json", body=json.dumps(payload)
                    )
            else:
                raise AssertionError("unexpected fixture network route")

        page.route("**/*", route)
        page.goto("http://owned.test/")
        expect(page.locator("[data-github-stars]")).to_have_text("7")
        expect(page.locator("[data-github-stars]").locator("..")).to_have_attribute(
            "aria-label", "7 stars: scitex-sdk"
        )
        page.clock.fast_forward(60001)
        expect(page.locator("[data-github-stars]")).to_have_text("8")
        for _ in range(3):
            with page.expect_response(
                "http://owned.test/api/landing/github-counts/"
            ) as response:
                page.clock.fast_forward(60001)
            response.value.body()
            page.evaluate("Promise.resolve()")
            expect(page.locator("[data-github-stars]")).to_have_text("8")
        assert len(calls) == 5
        assert all(
            "cookie" not in headers and "authorization" not in headers
            for headers in calls
        )
        browser.close()
    print(
        "PASS: initial/periodic refresh; 503/invalid/source-fallback retention; accessible counts; credential omission"
    )


if __name__ == "__main__":
    main()
