/**
 * Load-error fallback banner (UX standard: failures render an error state,
 * never a blank page).
 *
 * A failed script/stylesheet (restart window, stale manifest, CDN outage)
 * otherwise leaves interactive regions blank with zero explanation — the
 * exact shape of the FigRecipe blank-shell report (2026-10-16), where the
 * server HTML rendered and the JS never arrived. This module shows a
 * dismissible banner with a reload action the first time a resource fails
 * to load or an unhandled rejection surfaces, so the failure is visible
 * and recoverable instead of silent.
 *
 * Self-contained on purpose: no imports, no framework, no dependency on
 * any other bundle. It only needs its own entry to resolve.
 *
 * Mobile guarantees (operator 2026-10-19): the banner is bottom-fixed, so
 * the box itself is pointer-events:none (Reload/Dismiss stay auto) and the
 * detail text wraps anywhere — a long unbroken resource token must wrap,
 * never overflow unclipped, and taps must always reach inputs beneath it.
 */

const BANNER_ID = "stx-load-error-banner";
let shown = false;

function showBanner(detail: string): void {
  if (shown) return;
  shown = true;
  const banner = document.createElement("div");
  banner.id = BANNER_ID;
  banner.setAttribute("role", "alert");
  banner.style.cssText = [
    "position:fixed",
    "left:50%",
    "transform:translateX(-50%)",
    // Phone launcher (operator photos CCT4814/4815): the site dock owns the
    // bottom edge, so a bottom:16px banner sits ON the bottom nav. Clear it
    // with the shared dock token (live height + gap + safe-area); fallback
    // keeps the old offset where the dock stylesheet never loaded.
    "bottom:calc(var(--site-dock-scroll-clearance, 0px) + 16px)",
    "z-index:99999",
    // Mobile (operator 2026-10-19, CCT4763): the banner is bottom-fixed over
    // the form, so it must never intercept taps meant for inputs beneath it
    // (e.g. the signup password field with the keyboard open). None on the
    // box, auto on the two buttons: visible and actionable, never blocking.
    "pointer-events:none",
    "max-width:min(92vw,560px)",
    // Same report: the detail is a raw URL tail (font css2 query, hashed
    // chunk) with no spaces, so without wrapping it overflows unclipped.
    "overflow-wrap:anywhere",
    "word-break:break-word",
    // Longhand, not the background/border shorthands: jsdom's CSS parser
    // aborts the whole cssText block on shorthand+longhand mixes, which
    // makes the banner untestable in CI. Identical rendering in browsers.
    "background-color:#1f2937",
    "color:#f9fafb",
    "border:1px solid #b8956a",
    "border-radius:10px",
    "padding:10px 14px",
    "font-size:13px",
    "line-height:1.4",
    "box-shadow:0 8px 30px rgba(0,0,0,.45)",
  ].join(";");
  const text = document.createElement("span");
  text.textContent =
    "Something failed to load (" + detail + "). Reload to retry.";
  const reload = document.createElement("button");
  reload.type = "button";
  reload.textContent = "Reload";
  reload.style.cssText = [
    "margin-left:10px",
    "background-color:#b8956a",
    "color:#111",
    "border:0",
    "border-radius:6px",
    "padding:4px 12px",
    "font-weight:600",
    "cursor:pointer",
    "pointer-events:auto",
  ].join(";");
  reload.addEventListener("click", () => window.location.reload());
  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.textContent = "Dismiss";
  dismiss.setAttribute("aria-label", "Dismiss load error notice");
  dismiss.style.cssText = [
    "margin-left:6px",
    "background-color:transparent",
    "color:#f9fafb",
    "border:1px solid #6b7280",
    "border-radius:6px",
    "padding:4px 10px",
    "cursor:pointer",
    "pointer-events:auto",
  ].join(";");
  dismiss.addEventListener("click", () => banner.remove());
  banner.append(text, reload, dismiss);
  document.body.append(banner);
}

function describeTarget(target: EventTarget | null): string | null {
  const el = target as HTMLElement | null;
  if (!el || !el.tagName) return null;
  const tag = el.tagName.toLowerCase();
  if (tag !== "script" && tag !== "link" && tag !== "img") return null;
  const src =
    el.getAttribute("src") ||
    el.getAttribute("href") ||
    el.getAttribute("data-entry") ||
    tag;
  return src.split("/").pop() || tag;
}

function initLoadErrorBanner(): void {
  // Capture phase: resource errors do not bubble.
  window.addEventListener(
    "error",
    (event) => {
      const detail = describeTarget(event.target);
      if (detail) showBanner(detail);
    },
    true,
  );
  window.addEventListener("unhandledrejection", () => {
    showBanner("background task");
  });
}

initLoadErrorBanner();

export { initLoadErrorBanner, BANNER_ID };
