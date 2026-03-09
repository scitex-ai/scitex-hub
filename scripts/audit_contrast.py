#!/usr/bin/env python3
"""Audit button/link text contrast across all SciTeX pages.

Usage:
    python scripts/audit_contrast.py [--base-url URL] [--threshold RATIO]

Requires: pip install playwright && playwright install chromium
"""

import argparse
import json
import sys

from playwright.sync_api import sync_playwright

PAGES = [
    "/",
    "/writer/",
    "/scholar/",
    "/console/",
    "/vis/",
    "/clew/",
    "/apps/home/",
    "/tools/",
    "/releases/",
    "/server-status/",
    "/about/",
    "/contributors/",
    "/setup/",
    "/terms/",
    "/privacy/",
    "/cookies/",
    "/pricing/",
    "/docs/web-api/",
    "/keyboard-shortcuts/",
]

CONTRAST_CHECK_JS = """
() => {
  function luminance(r, g, b) {
    const [rs, gs, bs] = [r, g, b].map(c => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  }

  function contrastRatio(l1, l2) {
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  function parseColor(str) {
    const m = str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
    if (!m) return null;
    return { r: +m[1], g: +m[2], b: +m[3] };
  }

  function getEffectiveBg(el) {
    let node = el;
    while (node) {
      const bg = getComputedStyle(node).backgroundColor;
      const parsed = parseColor(bg);
      if (parsed && !bg.includes(', 0)')) {
        return parsed;
      }
      node = node.parentElement;
    }
    return { r: 255, g: 255, b: 255 };  // assume white
  }

  const results = [];
  const selectors = 'button, a, .btn, [role="button"], input[type="submit"]';
  const elements = document.querySelectorAll(selectors);

  elements.forEach(el => {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    if (style.display === 'none' || style.visibility === 'hidden') return;
    if (style.opacity === '0') return;

    const text = (el.textContent || '').trim().substring(0, 60);
    if (!text) return;

    const fg = parseColor(style.color);
    if (!fg) return;

    const bg = getEffectiveBg(el);
    const fgLum = luminance(fg.r, fg.g, fg.b);
    const bgLum = luminance(bg.r, bg.g, bg.b);
    const ratio = contrastRatio(fgLum, bgLum);

    results.push({
      text: text,
      tag: el.tagName,
      classes: (el.className || '').toString().substring(0, 80),
      fg: style.color,
      bg: `rgb(${bg.r}, ${bg.g}, ${bg.b})`,
      ratio: Math.round(ratio * 100) / 100,
      wcaa_pass: ratio >= 4.5,
      wcaaa_pass: ratio >= 7.0,
    });
  });

  return results;
}
"""


def run_audit(base_url, threshold):
    failures = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        for theme in ["light", "dark"]:
            for path in PAGES:
                url = f"{base_url}{path}"
                label = f"[{theme}] {path}"
                try:
                    page.goto(url, wait_until="networkidle", timeout=15000)
                except Exception:
                    try:
                        page.goto(url, wait_until="load", timeout=15000)
                    except Exception as e:
                        print(f"  SKIP {label}: {e}")
                        continue

                # Set theme
                page.evaluate(
                    f"document.documentElement.setAttribute('data-theme', '{theme}')"
                )
                page.wait_for_timeout(300)

                try:
                    results = page.evaluate(CONTRAST_CHECK_JS)
                except Exception as e:
                    print(f"  SKIP {label}: JS error: {e}")
                    continue

                fails = [r for r in results if r["ratio"] < threshold]
                if fails:
                    failures[label] = fails

                n_total = len(results)
                n_fail = len(fails)
                status = "FAIL" if n_fail > 0 else "PASS"
                print(
                    f"  {status} {label}: {n_fail}/{n_total} elements below {threshold}:1"
                )

        browser.close()

    return failures


def print_report(failures, threshold):
    if not failures:
        print(f"\nAll elements pass WCAG AA contrast ({threshold}:1).")
        return

    # Deduplicate by CSS class
    class_issues = {}
    for label, fails in failures.items():
        for f in fails:
            key = f["classes"] or f["tag"]
            if key not in class_issues:
                class_issues[key] = {
                    "text_sample": f["text"],
                    "fg": f["fg"],
                    "bg": f["bg"],
                    "ratio": f["ratio"],
                    "pages": set(),
                }
            class_issues[key]["pages"].add(label)
            if f["ratio"] < class_issues[key]["ratio"]:
                class_issues[key]["ratio"] = f["ratio"]
                class_issues[key]["fg"] = f["fg"]
                class_issues[key]["bg"] = f["bg"]

    print(f"\n{'=' * 80}")
    print(f"CONTRAST AUDIT REPORT (threshold: {threshold}:1)")
    print(f"{'=' * 80}")
    print(f"\n{len(class_issues)} unique CSS classes/elements with contrast issues:\n")

    for cls, info in sorted(class_issues.items(), key=lambda x: x[1]["ratio"]):
        pages_list = ", ".join(sorted(info["pages"]))
        print(f"  Class: {cls}")
        print(f'    Sample: "{info["text_sample"][:40]}"')
        print(f"    FG: {info['fg']}  |  BG: {info['bg']}  |  Ratio: {info['ratio']}:1")
        print(f"    Pages: {pages_list}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Audit contrast across SciTeX pages")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL")
    parser.add_argument("--threshold", type=float, default=4.5, help="WCAG AA ratio")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    print(f"Auditing contrast on {args.base_url} (threshold: {args.threshold}:1)")
    print(f"Pages: {len(PAGES)} x 2 themes = {len(PAGES) * 2} checks\n")

    failures = run_audit(args.base_url, args.threshold)

    if args.json:
        # Convert sets to lists for JSON
        for v in failures.values():
            for f in v:
                pass
        print(json.dumps(failures, indent=2))
    else:
        print_report(failures, args.threshold)

    n_total = sum(len(f) for f in failures.values())
    print(f"\nTotal failing elements: {n_total}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
