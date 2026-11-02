#!/usr/bin/env python3
"""Real Chromium: installed SDK FilterField plus Hub matching and AJAX loader."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from scitex_logging import getPlainConsole


def verify(repo: Path, sdk: Path, chromium: str, typescript: str) -> dict:
    app = repo / "apps/workspace/my_projects_app"
    source = app / "static/my_projects_app/ts"
    from django.conf import settings
    from django.template import Context, Engine

    if not settings.configured:
        settings.configure(USE_I18N=False, USE_TZ=True, STATIC_URL="/static/")
    template = (
        app / "templates/my_projects_app/partials/user_profile_content.html"
    ).read_text()
    now = datetime.now(timezone.utc)
    projects = [
        SimpleNamespace(
            id=index,
            name=name,
            slug=slug,
            effective_owner_slug="fixture",
            visibility="private",
            description=description,
            topics_list=[topic],
            updated_at=now,
        )
        for index, name, slug, description, topic in [
            (1, "BrainAtlas", "brain", "Neurobiology", "imaging"),
            (2, "GenomeLibrary", "genes", "Sequencing", "biology"),
        ]
    ]
    engine = Engine(
        libraries={
            "static": "django.templatetags.static",
            "i18n": "django.templatetags.i18n",
        }
    )
    fragment = engine.from_string(template).render(
        Context(
            {
                "profile_user": SimpleNamespace(username="fixture", date_joined=now),
                "user": SimpleNamespace(username="fixture"),
                "is_own_projects": True,
                "projects": projects,
                "followers_count": 0,
                "following_count": 0,
            }
        )
    )
    modules = {}
    imported_css = {}
    inputs = {
        name: source / f"{name}.ts"
        for name in (
            "hub-repo-filter",
            "hub-me-tab",
            "hub-navigate",
            "hub-api",
            "hub-url",
        )
    }
    inputs["csrf"] = repo / "static/shared/ts/utils/csrf.ts"
    for name, path in inputs.items():
        code = subprocess.check_output(
            [
                "node",
                "-e",
                "const ts=require(process.argv[1]),fs=require('fs');process.stdout.write(ts.transpileModule(fs.readFileSync(process.argv[2],'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText)",
                typescript,
                str(path),
            ],
            text=True,
        )
        code = re.sub(r'from "(\./[^\"]+)"', lambda m: f'from "{m[1]}.js"', code)

        def collect_css(match, base=path.parent):
            stylesheet = (base / match[1]).resolve()
            imported_css[f"/imported-css/{len(imported_css)}.css"] = stylesheet
            return ""

        code = re.sub(r'^import "([^\"]+\.css)";?$', collect_css, code, flags=re.M)
        modules[f"/{name}.js"] = code.replace('"@utils/csrf"', '"/csrf.js"')
    root = sdk / "ui/static/scitex_sdk/ui"
    host_css = app / "static/my_projects_app/css"
    links = "".join(f'<link rel="stylesheet" href="{url}">' for url in imported_css)
    html = (
        '<html><head><link rel="stylesheet" href="/sdk/filter.css"><link rel="stylesheet" href="/shared-css/primitives/typography.css"><link rel="stylesheet" href="/hub-css/hub.css">'
        + links
        + '<style>html{font-size:14px;scrollbar-gutter:stable}body{margin:0;font-family:Arial,sans-serif}*{box-sizing:border-box}</style></head><body><main class="hub-main" data-username="fixture" data-sdk-filter-module="/sdk/filter.js"><section id="hub-main-content">'
        + fragment
        + "</section></main></body></html>"
    )

    rows = []
    mutations = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chromium, headless=True)
        for width in (1440, 390):
            page = browser.new_page(viewport={"width": width, "height": 844})

            def route(request):
                path = urlsplit(request.request.url).path
                if request.request.method not in ("GET", "HEAD", "OPTIONS"):
                    mutations.append({"method": request.request.method, "path": path})
                    request.fulfill(
                        status=409, json={"error": "Owned fixture is read-only"}
                    )
                    return
                if path in modules:
                    request.fulfill(content_type="text/javascript", body=modules[path])
                elif path == "/sdk/filter.js":
                    request.fulfill(
                        content_type="text/javascript",
                        body=(root / "js/app/filter-field.js").read_text(),
                    )
                elif path == "/sdk/filter.css":
                    request.fulfill(
                        content_type="text/css",
                        body=(root / "css/app/filter-field.css").read_text(),
                    )
                elif path in imported_css:
                    request.fulfill(
                        content_type="text/css", body=imported_css[path].read_text()
                    )
                elif path.startswith("/hub-css/"):
                    request.fulfill(
                        content_type="text/css",
                        body=(host_css / path.removeprefix("/hub-css/")).read_text(),
                    )
                elif path.startswith("/shared-css/"):
                    request.fulfill(
                        content_type="text/css",
                        body=(
                            repo
                            / "static/shared/css"
                            / path.removeprefix("/shared-css/")
                        ).read_text(),
                    )
                elif path == "/apps/my-projects/api/me/":
                    request.fulfill(json={"success": True, "html": fragment})
                else:
                    request.fulfill(content_type="text/html", body=html)

            page.route("**/*", route)
            page.goto("https://owned-fixture.invalid/")
            page.evaluate(
                """async()=>{window.filterModule=await import('/hub-repo-filter.js');window.me=await import('/hub-me-tab.js');window.navigate=await import('/hub-navigate.js');document.querySelector('.hub-main').addEventListener('input',e=>{if(e.target.id==='hub-repo-filter')window.me.filterRepoCards(e.target.value)});await window.filterModule.initRepoFilters()}"""
            )
            field = page.locator("#hub-repo-filter")
            geometry = page.evaluate(
                """()=>{const take=s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom}};return {header:take('.hub-repos-header'),title:take('.hub-repos-header h3'),action:take('.hub-new-project-btn'),filter:take('.hub-repo-filter-wrap'),input:take('#hub-repo-filter')}}"""
            )
            if geometry["input"]["width"] < 120:
                rows.append(
                    {
                        "width": width,
                        "geometry": geometry,
                        "passed": False,
                        "reason": "Project title/action squeeze the SDK input below a usable width",
                    }
                )
                page.close()
                continue
            idle = page.locator(".stx-filter-field__hint").inner_text()
            page.keyboard.press("Control+k")
            focused = field.evaluate("e=>document.activeElement===e")
            active_hint = page.locator(".stx-filter-field__hint").inner_text()
            field.fill("neuro")
            matching = page.locator(".hub-project-card-link:not(.hub-hidden)").count()
            field.fill("zzzz")
            empty = page.locator("#hub-repo-no-results").is_visible()
            field.press("Escape")
            cleared = (
                field.input_value() == ""
                and page.locator(".hub-project-card-link:not(.hub-hidden)").count() == 2
            )
            blurred = field.evaluate("e=>document.activeElement!==e")
            field.click()
            mouse_hint = page.locator(".stx-filter-field__hint").inner_text()
            page.evaluate(
                "async()=>{await window.navigate.loadMe();await window.filterModule.initRepoFilters()}"
            )
            page.keyboard.press("Control+k")
            remounted = (
                field.evaluate("e=>document.activeElement===e")
                and page.locator("#hub-repo-filter").count() == 1
            )
            row = {
                "width": width,
                "geometry": geometry,
                "full_phone_filter_row": width > 768
                or (
                    abs(geometry["filter"]["width"] - geometry["header"]["width"]) < 1
                    and geometry["filter"]["y"]
                    >= max(geometry["title"]["bottom"], geometry["action"]["bottom"])
                ),
                "placeholder": field.get_attribute("placeholder"),
                "icon_first": page.locator("[data-stx-filter-field]").evaluate(
                    "e=>e.firstElementChild.tagName.toLowerCase()==='svg'"
                ),
                "idle_hint": idle,
                "focused": focused,
                "active_hint": active_hint,
                "matching_rows": matching,
                "empty_state": empty,
                "escape_clear": cleared,
                "escape_blur": blurred,
                "mouse_hint": mouse_hint,
                "ajax_loadMe_remount": remounted,
            }
            row["passed"] = all(
                (
                    row["placeholder"] == "Filter projects with keywords",
                    row["icon_first"],
                    row["full_phone_filter_row"],
                    idle == "Ctrl+K",
                    focused,
                    active_hint == "Esc",
                    matching == 1,
                    empty,
                    cleared,
                    blurred,
                    mouse_hint == "Esc",
                    remounted,
                )
            )
            rows.append(row)
            page.close()
        browser.close()
    return {
        "rows": rows,
        "passed": all(row["passed"] for row in rows) and not mutations,
        "blocked_fixture_mutations": mutations,
        "scope": "Owned fixture only; real Hub controller, AJAX loader and installed SDK module; no user data or live requests",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-package-root", type=Path, required=True)
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--typescript", required=True)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[2]
    )
    args = parser.parse_args()
    result = verify(args.repo, args.sdk_package_root, args.chromium, args.typescript)
    getPlainConsole(__name__).emit(json.dumps(result))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
