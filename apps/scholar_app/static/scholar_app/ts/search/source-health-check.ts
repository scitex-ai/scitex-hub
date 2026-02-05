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
    } else {
      const tooltip = `${data.service}: Unavailable - ${data.error || "Database not loaded"}`;
      updateIndicator(elements.ready, "unavailable", tooltip);
      updateIndicator(elements.led, "unavailable", tooltip);
    }
  } catch (error) {
    console.error(`[HealthCheck] Failed to check ${sourceName}:`, error);
    const tooltip = `${sourceName}: Error - Unable to reach health endpoint`;
    updateIndicator(elements.ready, "unavailable", tooltip);
    updateIndicator(elements.led, "unavailable", tooltip);
  }
}

/**
 * Initialize health checks on page load
 */
function initHealthChecks(): void {
  console.log("[HealthCheck] Initializing source health checks...");

  // Set initial "checking" state for header LEDs
  updateIndicator("ledCrossrefLocal", "checking", "Checking availability...");
  updateIndicator("ledOpenalexLocal", "checking", "Checking availability...");

  // Check local databases
  checkSourceHealth("crossref_local");
  checkSourceHealth("openalex_local");

  console.log("[HealthCheck] Health checks initiated");
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
