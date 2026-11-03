/* Public GitHub counters: initial + visible 60s refresh, server cache bounds API use. */
export function applyGitHubCounts(root, payload) {
  if (!payload || !payload.repositories || !["fresh", "stale", "snapshot"].includes(payload.status)) return;
  const timestamp = Date.parse(payload.fetched_at || "");
  const previous = Number(root.dataset.githubCountsTime || 0);
  if (previous && (!Number.isFinite(timestamp) || timestamp < previous)) return;
  for (const card of root.querySelectorAll("[data-github-repo]")) {
    const row = payload.repositories[card.dataset.githubRepo];
    if (!row || row.available !== true || !Number.isSafeInteger(row.stars) || row.stars < 0 || !Number.isSafeInteger(row.forks) || row.forks < 0) continue;
    // Never replace an already-rendered last-known number with source fallback.
    if (payload.status === "snapshot" && !card.querySelector("[data-github-count-link][hidden]")) continue;
    card.querySelector("[data-github-stars]").textContent = String(row.stars);
    card.querySelector("[data-github-forks]").textContent = String(row.forks);
    for (const [selector, count] of [["[data-github-stars]", row.stars], ["[data-github-forks]", row.forks]]) {
      const link = card.querySelector(selector).closest("a");
      link.setAttribute("aria-label", `${count} ${link.dataset.githubLabel}: ${card.dataset.githubRepo}`);
    }
    for (const link of card.querySelectorAll("[data-github-count-link]")) link.hidden = false;
    card.querySelector("[data-github-unavailable]").hidden = true;
  }
  if (payload.status !== "snapshot" && Number.isFinite(timestamp)) root.dataset.githubCountsTime = String(timestamp);
}

export function startGitHubCounts(root) {
  if (root.dataset.githubCountsMounted) return;
  const url = new URL(root.dataset.githubCountsUrl, location.href);
  if (url.origin !== location.origin) return;
  root.dataset.githubCountsMounted = "true";
  let pending = false;
  async function refresh() {
    if (pending || document.visibilityState === "hidden") return;
    pending = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(url, { credentials: "omit", cache: "no-store", headers: { Accept: "application/json" }, signal: controller.signal });
      if (response.ok) applyGitHubCounts(root, await response.json());
    } catch { /* Keep visible last-known counts; no fabricated zero or error banner. */ }
    finally { clearTimeout(timeout); pending = false; }
  }
  refresh();
  setInterval(refresh, 60000);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") refresh(); });
}

for (const root of document.querySelectorAll("[data-github-counts-url]")) startGitHubCounts(root);
