#!/usr/bin/env node
// -*- coding: utf-8 -*-
// Timestamp: 2026-02-13
// Author: ywatanabe (with Claude Code)
// File: /home/ywatanabe/proj/scitex-hub/scripts/maintenance/_check_contrast_worker.js
//
// Playwright-based WCAG AA contrast checker for SciTeX Cloud.
// Visits each page, evaluates computed styles, and reports violations.

const { chromium } = require("playwright");

// ── WCAG contrast utilities ──────────────────────────────────────
function parseColor(str) {
  if (!str) return null;
  const rgba = str.match(
    /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)/,
  );
  if (rgba) {
    return {
      r: parseInt(rgba[1]),
      g: parseInt(rgba[2]),
      b: parseInt(rgba[3]),
      a: rgba[4] !== undefined ? parseFloat(rgba[4]) : 1,
    };
  }
  return null;
}

function sRGBtoLinear(c) {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

function relativeLuminance(rgb) {
  return (
    0.2126 * sRGBtoLinear(rgb.r) +
    0.7152 * sRGBtoLinear(rgb.g) +
    0.0722 * sRGBtoLinear(rgb.b)
  );
}

function contrastRatio(fg, bg) {
  const lFg = relativeLuminance(fg);
  const lBg = relativeLuminance(bg);
  const lighter = Math.max(lFg, lBg);
  const darker = Math.min(lFg, lBg);
  return (lighter + 0.05) / (darker + 0.05);
}

function blendOnBackground(fg, bg) {
  const a = fg.a;
  return {
    r: Math.round(fg.r * a + bg.r * (1 - a)),
    g: Math.round(fg.g * a + bg.g * (1 - a)),
    b: Math.round(fg.b * a + bg.b * (1 - a)),
    a: 1,
  };
}

// ── Configuration ────────────────────────────────────────────────
const PAGES = [
  { path: "/", name: "Landing" },
  { path: "/tools/", name: "Tools" },
  { path: "/api-docs/", name: "API Docs" },
  { path: "/api-docs/scholar-api/", name: "Scholar API" },
  { path: "/api-docs/plot-api/", name: "Plot API" },
  { path: "/api-docs/stats-api/", name: "Stats API" },
  { path: "/dev/tests/", name: "Dev Tests" },
];

const THEMES = ["light", "dark"];

// WCAG AA thresholds
const RATIO_NORMAL = 4.5;
const RATIO_LARGE = 3.0;

// ── Page evaluation function (injected into browser) ─────────────
// This function runs inside the browser context.
function evaluateContrastInPage() {
  const results = [];
  const seen = new Set();

  function getRGB(str) {
    if (!str) return null;
    const m = str.match(
      /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\)/,
    );
    if (m)
      return {
        r: +m[1],
        g: +m[2],
        b: +m[3],
        a: m[4] !== undefined ? +m[4] : 1,
      };
    return null;
  }

  function getEffectiveBg(el) {
    let node = el;
    while (node && node !== document.documentElement) {
      const style = window.getComputedStyle(node);
      const bg = getRGB(style.backgroundColor);
      if (bg && bg.a > 0.01) return bg;
      node = node.parentElement;
    }
    // Fallback: assume white for light, dark for dark
    const theme = document.documentElement.getAttribute("data-theme");
    if (theme === "dark") return { r: 15, g: 20, b: 25, a: 1 };
    return { r: 248, g: 247, b: 245, a: 1 };
  }

  function srgb(c) {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  }

  function lum(rgb) {
    return 0.2126 * srgb(rgb.r) + 0.7152 * srgb(rgb.g) + 0.0722 * srgb(rgb.b);
  }

  function ratio(fg, bg) {
    const l1 = Math.max(lum(fg), lum(bg));
    const l2 = Math.min(lum(fg), lum(bg));
    return (l1 + 0.05) / (l2 + 0.05);
  }

  function blend(fg, bg) {
    const a = fg.a;
    return {
      r: Math.round(fg.r * a + bg.r * (1 - a)),
      g: Math.round(fg.g * a + bg.g * (1 - a)),
      b: Math.round(fg.b * a + bg.b * (1 - a)),
      a: 1,
    };
  }

  // Gather all visible text-bearing elements
  const textEls = document.querySelectorAll(
    "p, span, a, h1, h2, h3, h4, h5, h6, li, td, th, label, " +
      "button, input, textarea, select, code, pre, small, strong, " +
      "em, dt, dd, figcaption, blockquote, summary, legend",
  );

  for (const el of textEls) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue;

    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") continue;
    if (parseFloat(style.opacity) < 0.1) continue;

    const text = (el.textContent || "").trim();
    if (!text) continue;

    const fgColor = getRGB(style.color);
    if (!fgColor) continue;

    const bgColor = getEffectiveBg(el);
    if (!bgColor) continue;

    const effectiveFg = fgColor.a < 1 ? blend(fgColor, bgColor) : fgColor;
    const effectiveBg =
      bgColor.a < 1
        ? blend(bgColor, { r: 255, g: 255, b: 255, a: 1 })
        : bgColor;

    const cr = ratio(effectiveFg, effectiveBg);
    const fontSize = parseFloat(style.fontSize);
    const fontWeight = parseInt(style.fontWeight) || 400;
    const isLarge = fontSize >= 18 || (fontSize >= 14 && fontWeight >= 700);
    const required = isLarge ? 3.0 : 4.5;

    // Build a CSS selector path for reporting
    let selector = el.tagName.toLowerCase();
    if (el.id) selector += "#" + el.id;
    if (el.className && typeof el.className === "string") {
      selector += "." + el.className.trim().split(/\s+/).slice(0, 2).join(".");
    }

    // Deduplicate by selector + color combo
    const key = `${selector}|${style.color}|${style.backgroundColor}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const snippet = text.length > 40 ? text.substring(0, 40) + "..." : text;

    results.push({
      selector,
      snippet,
      fgStr: style.color,
      bgStr: style.backgroundColor || "(inherited)",
      ratio: Math.round(cr * 100) / 100,
      required,
      isLarge,
      fontSize: Math.round(fontSize * 10) / 10,
      fontWeight,
      pass: cr >= required,
    });
  }

  return results;
}

// ── Main ─────────────────────────────────────────────────────────
async function main() {
  const baseUrl = process.argv[2] || "http://127.0.0.1:8000";

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (err) {
    console.error("ERROR: Could not launch Playwright browser.");
    console.error(err.message);
    console.error("Try: npx playwright install chromium");
    process.exit(1);
  }

  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });

  let totalPass = 0;
  let totalFail = 0;
  const allViolations = [];

  for (const theme of THEMES) {
    console.log("");
    console.log(`--- Theme: ${theme} ---`);
    console.log("");

    for (const pageDef of PAGES) {
      const url = baseUrl + pageDef.path;
      const page = await context.newPage();

      try {
        const resp = await page.goto(url, {
          waitUntil: "domcontentloaded",
          timeout: 10000,
        });

        if (!resp || resp.status() >= 400) {
          console.log(
            `  SKIP  ${pageDef.name} (${pageDef.path}) - HTTP ${resp ? resp.status() : "no response"}`,
          );
          await page.close();
          continue;
        }

        // Set theme
        await page.evaluate((t) => {
          document.documentElement.setAttribute("data-theme", t);
        }, theme);

        // Wait for repaint
        await page.waitForTimeout(300);

        const results = await page.evaluate(evaluateContrastInPage);

        let pageFail = 0;
        let pagePass = 0;

        for (const r of results) {
          if (r.pass) {
            pagePass++;
            totalPass++;
          } else {
            pageFail++;
            totalFail++;
            allViolations.push({
              theme,
              page: pageDef.name,
              path: pageDef.path,
              ...r,
            });
          }
        }

        const status = pageFail > 0 ? "FAIL" : "PASS";
        const color = pageFail > 0 ? "\x1b[31m" : "\x1b[32m";
        console.log(
          `  ${color}${status}\x1b[0m  ${pageDef.name} (${pageDef.path}) ` +
            `- ${pagePass} pass, ${pageFail} fail`,
        );

        // Print violations inline
        if (pageFail > 0) {
          for (const r of results.filter((x) => !x.pass)) {
            const sizeInfo = r.isLarge ? "large" : "normal";
            console.log(
              `        \x1b[31m${r.ratio}:1\x1b[0m < ${r.required}:1 (${sizeInfo} ${r.fontSize}px/${r.fontWeight}) ` +
                `${r.selector} fg=${r.fgStr} bg=${r.bgStr}`,
            );
            console.log(`          "${r.snippet}"`);
          }
        }
      } catch (err) {
        console.log(
          `  SKIP  ${pageDef.name} (${pageDef.path}) - ${err.message.split("\n")[0]}`,
        );
      }

      await page.close();
    }
  }

  await browser.close();

  // Summary
  console.log("");
  console.log("=== Summary ===");
  console.log(`Total elements checked: ${totalPass + totalFail}`);
  console.log(`  PASS: ${totalPass}`);
  console.log(`  FAIL: ${totalFail}`);

  if (allViolations.length > 0) {
    console.log("");
    console.log("=== Violation Details ===");

    // Group by theme
    for (const theme of THEMES) {
      const tv = allViolations.filter((v) => v.theme === theme);
      if (tv.length === 0) continue;
      console.log(`\n  [${theme}] ${tv.length} violations:`);
      for (const v of tv) {
        console.log(
          `    ${v.page} | ${v.selector} | ratio=${v.ratio}:1 required=${v.required}:1 | fg=${v.fgStr} bg=${v.bgStr}`,
        );
      }
    }
  }

  console.log("");
  if (totalFail > 0) {
    console.log(
      "\x1b[31mWCAG AA contrast check FAILED with " +
        totalFail +
        " violation(s).\x1b[0m",
    );
    process.exit(1);
  } else {
    console.log("\x1b[32mWCAG AA contrast check PASSED.\x1b[0m");
    process.exit(0);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err.message);
  process.exit(1);
});
