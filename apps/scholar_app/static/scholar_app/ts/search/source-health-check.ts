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

// Map source names to their element IDs (ready indicator + header LED)
const SOURCE_ELEMENTS: Record<string, { ready: string; led: string }> = {
  crossref_local: { ready: "readyCrossrefLocal", led: "ledCrossrefLocal" },
  openalex_local: { ready: "readyOpenalexLocal", led: "ledOpenalexLocal" },
};

/**
 * Update indicator element status
 */
function updateIndicator(
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
  const elements = SOURCE_ELEMENTS[sourceName];
  if (!endpoint || !elements) {
    console.warn(`[HealthCheck] No endpoint for source: ${sourceName}`);
    return;
  }

  try {
    const response = await fetch(endpoint);
    const data: HealthResponse = await response.json();

    if (data.ready) {
      const tooltip = `${data.service}: Ready - Local database available`;
      updateIndicator(elements.ready, "ready", tooltip);
      updateIndicator(elements.led, "ready", tooltip);
      updateSourceItemStatus(sourceName, true);
    } else {
      const tooltip = `${data.service}: Unavailable - ${data.error || "Database not loaded"}`;
      updateIndicator(elements.ready, "unavailable", tooltip);
      updateIndicator(elements.led, "unavailable", tooltip);
      updateSourceItemStatus(sourceName, false);
    }
  } catch (error) {
    console.error(`[HealthCheck] Failed to check ${sourceName}:`, error);
    const tooltip = `${sourceName}: Error - Unable to reach health endpoint`;
    updateIndicator(elements.ready, "unavailable", tooltip);
    updateIndicator(elements.led, "unavailable", tooltip);
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

  // Set initial "checking" state for header LEDs
  updateIndicator("ledCrossrefLocal", "checking", "Checking availability...");
  updateIndicator("ledOpenalexLocal", "checking", "Checking availability...");

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
  const elements = SOURCE_ELEMENTS[sourceName];
  if (elements) {
    const tooltip = `${sourceName}: Searching...`;
    updateIndicator(elements.ready, "working", tooltip);
    updateIndicator(elements.led, "searching", tooltip);
  }
}

export function setSourceReady(sourceName: string): void {
  const elements = SOURCE_ELEMENTS[sourceName];
  if (elements) {
    const tooltip = `${sourceName}: Ready - Local database available`;
    updateIndicator(elements.ready, "ready", tooltip);
    updateIndicator(elements.led, "ready", tooltip);
  }
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", initHealthChecks);
