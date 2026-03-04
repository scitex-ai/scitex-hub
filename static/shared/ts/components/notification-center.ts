/**
 * Notification Center
 *
 * Synology-style notification bell in the global header.
 * Aggregates server health issues + browser-side JS errors.
 * Polls /api/server-health/ every 60s and captures window errors.
 */

interface HealthIssue {
  service: string;
  level: "error" | "warning";
  message: string;
}

interface BrowserError {
  source: string;
  message: string;
  timestamp: number;
}

// State
const browserErrors: BrowserError[] = [];
const MAX_BROWSER_ERRORS = 20;
let serverIssues: HealthIssue[] = [];
let pollIntervalId: number | null = null;

/**
 * Capture browser-side errors (Vite crashes, JS load failures, etc.)
 */
function setupBrowserErrorCapture(): void {
  // Script load failures (ERR_EMPTY_RESPONSE, etc.)
  window.addEventListener(
    "error",
    (event: ErrorEvent) => {
      // Only capture resource load errors, not regular JS errors
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "SCRIPT" || target.tagName === "LINK")
      ) {
        const src =
          (target as HTMLScriptElement).src ||
          (target as HTMLLinkElement).href ||
          "unknown";
        const filename = src.split("/").pop() || src;
        addBrowserError(filename, `Failed to load: ${filename}`);
      }
    },
    true,
  ); // useCapture to catch resource errors

  // Unhandled promise rejections (fetch failures, etc.)
  window.addEventListener(
    "unhandledrejection",
    (event: PromiseRejectionEvent) => {
      const msg = event.reason?.message || String(event.reason);
      // Skip noise from extensions, analytics, etc.
      if (msg.includes("extension") || msg.includes("chrome-extension")) return;
      addBrowserError("JS", msg.substring(0, 100));
    },
  );
}

function addBrowserError(source: string, message: string): void {
  // Deduplicate: don't add if same source+message exists
  const exists = browserErrors.some(
    (e) => e.source === source && e.message === message,
  );
  if (exists) return;

  browserErrors.push({ source, message, timestamp: Date.now() });

  // Cap at MAX
  if (browserErrors.length > MAX_BROWSER_ERRORS) {
    browserErrors.shift();
  }

  updateUI();
}

/**
 * Poll server health API
 */
async function fetchServerHealth(): Promise<void> {
  try {
    const resp = await fetch("/api/server-health/");
    if (!resp.ok) {
      serverIssues = [
        {
          service: "Health API",
          level: "error",
          message: `HTTP ${resp.status}`,
        },
      ];
      updateUI();
      return;
    }
    const data = await resp.json();
    serverIssues = data.issues || [];
    updateUI();
  } catch {
    serverIssues = [
      {
        service: "Server",
        level: "error",
        message: "Health check unreachable",
      },
    ];
    updateUI();
  }
}

/**
 * Update badge count and dropdown content
 */
function updateUI(): void {
  const badge = document.getElementById("notification-badge");
  const list = document.getElementById("notification-list");
  if (!badge || !list) return;

  // Merge server issues + browser errors into unified list
  const allIssues: { service: string; level: string; message: string }[] = [
    ...serverIssues,
    ...browserErrors.map((e) => ({
      service: e.source,
      level: "warning" as const,
      message: e.message,
    })),
  ];

  const count = allIssues.length;

  // Update badge
  if (count > 0) {
    badge.style.display = "flex";
    badge.textContent = String(count);
    // Red if any errors, yellow if only warnings
    const hasErrors = allIssues.some((i) => i.level === "error");
    badge.style.background = hasErrors ? "#ef4444" : "#eab308";
  } else {
    badge.style.display = "none";
  }

  // Update dropdown list
  if (count === 0) {
    list.innerHTML =
      '<div class="notification-empty">' +
      '<i class="fas fa-check-circle" style="color: #22c55e; margin-right: 6px"></i>' +
      "All systems operational</div>";
    return;
  }

  list.innerHTML = allIssues
    .map((issue) => {
      const icon =
        issue.level === "error"
          ? '<i class="fas fa-exclamation-circle" style="color: #ef4444"></i>'
          : '<i class="fas fa-exclamation-triangle" style="color: #eab308"></i>';
      return (
        `<div class="notification-item notification-${issue.level}">` +
        `<span class="notification-icon">${icon}</span>` +
        `<span class="notification-service">${escapeHtml(issue.service)}</span>` +
        `<span class="notification-message">${escapeHtml(issue.message)}</span>` +
        `</div>`
      );
    })
    .join("");
}

function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Initialize notification center
 */
function initNotificationCenter(): void {
  const bell = document.getElementById("notification-bell");
  const dropdown = document.getElementById("notification-dropdown");
  const clearBtn = document.getElementById("notification-clear");

  if (!bell || !dropdown) return;

  // Toggle dropdown on bell click
  bell.addEventListener("click", (e) => {
    e.stopPropagation();
    const isVisible = dropdown.style.display !== "none";
    dropdown.style.display = isVisible ? "none" : "block";
  });

  // Close on click outside
  document.addEventListener("click", (e) => {
    const center = document.getElementById("notification-center");
    if (center && !center.contains(e.target as Node)) {
      dropdown.style.display = "none";
    }
  });

  // Close on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      dropdown.style.display = "none";
    }
  });

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      browserErrors.length = 0;
      updateUI();
    });
  }

  // Capture browser errors
  setupBrowserErrorCapture();

  // Initial fetch + poll every 60s
  fetchServerHealth();
  pollIntervalId = window.setInterval(fetchServerHealth, 60000);
}

// Initialize
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initNotificationCenter);
} else {
  initNotificationCenter();
}
