/**
 * Compilation Log Management
 * Writes compilation logs directly to the Details panel.
 */

// Module-level active log type — replaces the old data-log-type attribute
// on the now-removed #compilation-output element.
let _activeLogType: "preview" | "full" = "full";

// Store separate logs for preview and full compilation
export const compilationLogs = {
  preview: "",
  full: "",
};

/**
 * Set the active log type so subsequent log writes go to the correct
 * Details panel section (preview or full).
 */
export function setActiveLogType(type: "preview" | "full"): void {
  _activeLogType = type;
}

/**
 * Get the active log type.
 */
export function getActiveLogType(): "preview" | "full" {
  return _activeLogType;
}

/**
 * Get the Details panel log element for the active compilation type.
 */
function getDetailsLog(): HTMLElement | null {
  const id =
    _activeLogType === "preview" ? "details-preview-log" : "details-full-log";
  return document.getElementById(id);
}

/**
 * Append to compilation log with semantic color coding and visual cues.
 * Writes directly to the Details panel log area.
 */
export function appendCompilationLog(
  message: string,
  type: "info" | "success" | "error" | "warning" | "processing" = "info",
  options?: { spinner?: boolean; dots?: boolean; id?: string },
): void {
  const log = getDetailsLog();
  if (!log) return;

  // Create line container
  const lineDiv = document.createElement("div");
  if (options?.id) {
    lineDiv.id = options.id;
  }

  // Add spinner if requested
  if (options?.spinner) {
    const spinner = document.createElement("span");
    spinner.className = "terminal-log__spinner";
    lineDiv.appendChild(spinner);
  }

  // Create colored span for the message
  const span = document.createElement("span");

  // Apply semantic color class based on message content or type
  if (
    message.includes("\u2713") ||
    message.includes("Success") ||
    type === "success"
  ) {
    span.className = "terminal-log__success";
  } else if (
    message.includes("\u2717") ||
    message.includes("Error") ||
    message.includes("Failed") ||
    type === "error"
  ) {
    span.className = "terminal-log__error";
  } else if (
    message.includes("\u26A0") ||
    message.includes("Warning") ||
    type === "warning"
  ) {
    span.className = "terminal-log__warning";
  } else if (type === "processing") {
    span.className = "terminal-log__processing";
  } else {
    span.className = "terminal-log__info";
  }

  span.textContent = message;
  lineDiv.appendChild(span);

  // Add animated dots if requested
  if (options?.dots) {
    const dots = document.createElement("span");
    dots.className = "terminal-log__loading-dots";
    lineDiv.appendChild(dots);
  }

  // Add newline
  lineDiv.appendChild(document.createTextNode("\n"));

  log.appendChild(lineDiv);

  // Auto-scroll to bottom
  log.scrollTop = log.scrollHeight;
}

/**
 * Update a processing log line (remove spinner/dots, update message)
 */
export function updateCompilationLog(
  lineId: string,
  message: string,
  type: "success" | "error" | "warning" | "info" = "info",
): void {
  const line = document.getElementById(lineId);
  if (!line) return;

  // Remove spinner and dots
  const spinner = line.querySelector(".terminal-log__spinner");
  const dots = line.querySelector(".terminal-log__loading-dots");
  if (spinner) spinner.remove();
  if (dots) dots.remove();

  // Update message
  const span = line.querySelector(
    "span:not(.terminal-log__spinner):not(.terminal-log__loading-dots)",
  );
  if (span) {
    span.textContent = message;

    // Update color class
    span.className = "";
    if (
      message.includes("\u2713") ||
      message.includes("Success") ||
      type === "success"
    ) {
      span.className = "terminal-log__success";
    } else if (
      message.includes("\u2717") ||
      message.includes("Error") ||
      message.includes("Failed") ||
      type === "error"
    ) {
      span.className = "terminal-log__error";
    } else if (
      message.includes("\u26A0") ||
      message.includes("Warning") ||
      type === "warning"
    ) {
      span.className = "terminal-log__warning";
    } else {
      span.className = "terminal-log__info";
    }
  }
}

/**
 * Expand a Details panel section by data-section key.
 */
function expandDetailsSection(sectionKey: string): void {
  const section = document.querySelector(
    `#writer-details-content [data-section="${sectionKey}"]`,
  );
  if (section) {
    section.classList.remove("collapsed");
    try {
      const states = JSON.parse(
        localStorage.getItem("writer-details-sections") || "{}",
      );
      states[sectionKey] = false;
      localStorage.setItem("writer-details-sections", JSON.stringify(states));
    } catch {
      /* ignore */
    }
  }
}

/**
 * Toggle preview compilation log — expands the preview section in Details panel.
 */
export function togglePreviewLog(): void {
  setActiveLogType("preview");
  expandDetailsSection("preview-log");
}

/**
 * Toggle full compilation log — expands the full section in Details panel.
 */
export function toggleFullLog(): void {
  setActiveLogType("full");
  expandDetailsSection("full-log");
}
