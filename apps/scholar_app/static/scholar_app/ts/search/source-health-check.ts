/**
 * Source Health Check
 *
 * Checks availability of local database sources on page load.
 * External APIs are always shown as "ready" (green).
 * Local sources check health endpoints and update status.
 *
 * Status colors:
 * - checking (gray, pulsing): Initial state, checking availability
 * - ready (green): Source is available
 * - working (green, flashing): Search in progress
 * - unavailable (red): Source is not available
 * - external (green): External API, always available
 */

interface HealthResponse {
  status: "healthy" | "unavailable" | "unhealthy";
  service: string;
  ready: boolean;
  error?: string;
}

const HEALTH_ENDPOINTS: Record<string, string> = {
  crossref_local: "/scholar/api/health/crossref-local/",
  openalex_local: "/scholar/api/health/openalex-local/",
};

// Map source names to their ready-indicator element IDs
const SOURCE_READY_IDS: Record<string, string> = {
  crossref_local: "readyCrossrefLocal",
  openalex_local: "readyOpenalexLocal",
};

/**
 * Update all LED indicators matching a data-source value.
 * Both pane-header LEDs and Sources-panel LEDs share data-source attributes.
 */
function updateLedsBySource(
  sourceName: string,
  status:
    | "checking"
    | "ready"
    | "working"
    | "searching"
    | "unavailable"
    | "external",
  tooltip: string,
): void {
  const leds = document.querySelectorAll<HTMLElement>(
    `.search-led[data-source="${sourceName}"]`,
  );
  leds.forEach((el) => {
    el.dataset.status = status;
    el.title = tooltip;
  });
}

/**
 * Update a single indicator element by ID
 */
function updateIndicatorById(
  elementId: string,
  status:
    | "checking"
    | "ready"
    | "working"
    | "searching"
    | "unavailable"
    | "external",
  tooltip: string,
): void {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.dataset.status = status;
  el.title = tooltip;
}

/**
 * Update the source item's count label and error class for idle-time status
 */
function updateSourceItemStatus(sourceName: string, available: boolean): void {
  const item = document.querySelector(
    `.source-item[data-source="${sourceName}"]`,
  ) as HTMLElement | null;
  if (!item) return;

  const countEl = item.querySelector(".count") as HTMLElement | null;
  if (available) {
    item.classList.remove("error");
    // Only clear ERR text if not mid-search
    if (countEl && countEl.textContent === "ERR") {
      countEl.textContent = "";
    }
  } else {
    item.classList.add("error");
    if (countEl) countEl.textContent = "ERR";
  }
}

/**
 * Check health of a local database source
 * Updates both the inline ready indicator and header LED
 */
async function checkSourceHealth(sourceName: string): Promise<void> {
  const endpoint = HEALTH_ENDPOINTS[sourceName];
  if (!endpoint) {
    console.warn(`[HealthCheck] No endpoint for source: ${sourceName}`);
    return;
  }

  const readyId = SOURCE_READY_IDS[sourceName];

  try {
    const response = await fetch(endpoint);
    const data: HealthResponse = await response.json();

    if (data.ready) {
      const tooltip = `${data.service}: Ready - Local database available`;
      updateLedsBySource(sourceName, "ready", tooltip);
      if (readyId) updateIndicatorById(readyId, "ready", tooltip);
      updateSourceItemStatus(sourceName, true);
    } else {
      const tooltip = `${data.service}: Unavailable - ${data.error || "Database not loaded"}`;
      updateLedsBySource(sourceName, "unavailable", tooltip);
      if (readyId) updateIndicatorById(readyId, "unavailable", tooltip);
      updateSourceItemStatus(sourceName, false);
    }
  } catch (error) {
    console.error(`[HealthCheck] Failed to check ${sourceName}:`, error);
    const tooltip = `${sourceName}: Error - Unable to reach health endpoint`;
    updateLedsBySource(sourceName, "unavailable", tooltip);
    if (readyId) updateIndicatorById(readyId, "unavailable", tooltip);
    updateSourceItemStatus(sourceName, false);
  }
}

// Health check polling interval (ms)
const HEALTH_CHECK_INTERVAL = 30_000; // 30 seconds
let healthCheckTimer: ReturnType<typeof setInterval> | null = null;

/**
 * Run health checks for all local sources
 */
function runHealthChecks(): void {
  checkSourceHealth("crossref_local");
  checkSourceHealth("openalex_local");
}

/**
 * Initialize health checks on page load with periodic polling
 */
function initHealthChecks(): void {
  console.log("[HealthCheck] Initializing source health checks...");

  // Set initial "checking" state for all LEDs (pane-header + Sources panel)
  updateLedsBySource("crossref_local", "checking", "Checking availability...");
  updateLedsBySource("openalex_local", "checking", "Checking availability...");

  // Run initial checks
  runHealthChecks();

  // Start periodic polling so LEDs reflect real-time connection status
  if (healthCheckTimer) clearInterval(healthCheckTimer);
  healthCheckTimer = setInterval(runHealthChecks, HEALTH_CHECK_INTERVAL);

  console.log(
    `[HealthCheck] Health checks initiated (polling every ${HEALTH_CHECK_INTERVAL / 1000}s)`,
  );
}

// Export for use by search system to show "working" status
export function setSourceWorking(sourceName: string): void {
  const tooltip = `${sourceName}: Searching...`;
  updateLedsBySource(sourceName, "searching", tooltip);
  const readyId = SOURCE_READY_IDS[sourceName];
  if (readyId) updateIndicatorById(readyId, "working", tooltip);
}

export function setSourceReady(sourceName: string): void {
  const tooltip = `${sourceName}: Ready - Local database available`;
  updateLedsBySource(sourceName, "ready", tooltip);
  const readyId = SOURCE_READY_IDS[sourceName];
  if (readyId) updateIndicatorById(readyId, "ready", tooltip);
}

// Trim template whitespace from searchLog initial content
function trimSearchLog(): void {
  const el = document.getElementById("searchLog");
  if (el) el.textContent = (el.textContent || "").trim();
}

// Initialize on DOM ready (ES modules load deferred, so DOMContentLoaded may have already fired)
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    trimSearchLog();
    initHealthChecks();
  });
} else {
  trimSearchLog();
  initHealthChecks();
}
