"""Owned Chromium check of actual landing CSS and shared theme roles.

This is a component fixture, not a public-page/deployment acceptance claim.
"""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "apps/infra/public_app/static/public_app/css"
SDK_THEME = (
    files("scitex_sdk")
    .joinpath("ui/static/scitex_sdk/ui/css/shell/theme.css")
    .read_text()
)
BASE = (CSS / "landing-reference-v2.css").read_text()
LAYOUT = (CSS / "landing/target-layout.css").read_text()
THEME = (CSS / "landing/theme.css").read_text()
PARTIAL = (
    ROOT
    / "apps/infra/public_app/templates/public_app/landing_partials/landing_opensource.html"
).read_text()
FOOTER_STYLE = PARTIAL.split("<style>", 1)[1].split("</style>", 1)[0]


def main():
    """Prove semantic surface/text roles and compact visible footer sizing."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get(
                "SCITEX_TEST_CHROMIUM",
                "/home/ywatanabe/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell",
            )
        )
        page = browser.new_page(viewport={"width": 390, "height": 844})
        for mode in ("light", "dark"):
            page.set_content(
                f"""<html data-theme="{mode}"><head><style>{SDK_THEME}{BASE}{LAYOUT}{THEME}</style></head><body>
<section class="landing-v2-hero"><h1>Overview</h1><p class="landing-v2-lead">Description</p>
<div class="landing-v2-carousel"><div class="landing-v2-carousel-controls"><button>Next</button></div><div class="landing-v2-carousel-track"><figcaption><strong>Caption</strong></figcaption></div></div></section>
<section class="landing-v2-section landing-v2-clew"><h2>Provenance</h2><figure class="landing-v2-clew-figure">Unchanged image container</figure></section>
<section class="landing-v2-section landing-v2-demo"><h2>Demo</h2></section>
<section class="landing-v2-section landing-v2-oss"><ul class="landing-oss-packages"><li style="width:240px;box-sizing:border-box"><h4>Repository</h4><p>Description</p><div class="landing-oss-counts"><a>◉ GitHub</a><a>☆ 86 stars</a><a>⑂ 20 forks</a></div></li></ul></section>
<section class="section-pricing"><h2>Pricing</h2></section><style>{FOOTER_STYLE}</style></body></html>"""
            )
            result = page.evaluate(
                """() => {
              const root=getComputedStyle(document.documentElement);
              const probe=document.createElement('span');document.body.append(probe);
              const role=name=>{probe.style.color=root.getPropertyValue(name);return getComputedStyle(probe).color};
              const pageRole=role('--bg-page'),surfaceRole=role('--bg-surface'),textRole=role('--text-primary');
              const sections=Array.from(document.querySelectorAll('section')).map(e=>({bg:getComputedStyle(e).backgroundColor,text:getComputedStyle(e).color}));
              const panels=Array.from(document.querySelectorAll('.landing-v2-carousel,.landing-v2-clew-figure,.landing-oss-packages li')).map(e=>getComputedStyle(e).backgroundColor);
              const footer=document.querySelector('.landing-oss-counts');
              return {sections,panels,pageRole,surfaceRole,textRole,footerFits:footer.scrollWidth<=footer.clientWidth,oneRow:new Set(Array.from(footer.children,e=>Math.round(e.getBoundingClientRect().top))).size===1};
            }"""
            )
            assert all(
                s == {"bg": result["pageRole"], "text": result["textRole"]}
                for s in result["sections"]
            ), (mode, result)
            assert all(bg == result["surfaceRole"] for bg in result["panels"]), (
                mode,
                result,
            )
            assert result["footerFits"] and result["oneRow"], (mode, result)
        browser.close()
    print(
        "PASS: light/dark five surfaces, panel roles, visible 240px footer single row"
    )


if __name__ == "__main__":
    main()
