/**
 * CompilationLogManager.ts
 * Manages compilation log display, including appending messages,
 * updating status, and handling log panel interactions.
 */

/**
 * Append to compilation log with semantic color coding and visual cues
 */
export function appendCompilationLog(
  message: string,
  type: "info" | "success" | "error" | "warning" | "processing" = "info",
  options?: { spinner?: boolean; dots?: boolean; id?: string },
): void {
  const log = document.getElementById("compilation-log-inline");
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
    message.includes("✓") ||
    message.includes("Success") ||
    type === "success"
  ) {
    span.className = "terminal-log__success";
  } else if (
    message.includes("✗") ||
    message.includes("Error") ||
    message.includes("Failed") ||
    type === "error"
  ) {
    span.className = "terminal-log__error";
  } else if (
    message.includes("⚠") ||
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
      message.includes("✓") ||
      message.includes("Success") ||
      type === "success"
    ) {
      span.className = "terminal-log__success";
    } else if (
      message.includes("✗") ||
      message.includes("Error") ||
      message.includes("Failed") ||
      type === "error"
    ) {
      span.className = "terminal-log__error";
    } else if (
      message.includes("⚠") ||
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
 * Handle compilation log Start button
 * Starts the appropriate compilation based on current log type (preview or full)
 */
export function handleCompilationLogStart(): void {
  const output = document.getElementById("compilation-output");
  if (!output) return;

  const logType = output.getAttribute("data-log-type") as
    | "preview"
    | "full"
    | null;

  if (logType === "preview") {
    // Start preview compilation
    console.log("[Writer] Starting preview compilation from log toolbar");
    if ((window as any).handlePreviewClick) {
      (window as any).handlePreviewClick();
    }
  } else if (logType === "full") {
    // Start full compilation
    console.log("[Writer] Starting full compilation from log toolbar");
    if ((window as any).handleFullCompileClick) {
      (window as any).handleFullCompileClick();
    }
  } else {
    const showToast =
      (window as any).showToast || ((msg: string) => console.log(msg));
    showToast(
      "Please click a status LED first to select compilation type",
      "warning",
    );
  }
}

/**
 * Handle compilation log Stop button
 * Stops the current compilation
 */
export function handleCompilationLogStop(): void {
  const output = document.getElementById("compilation-output");
  if (!output) return;

  const logType = output.getAttribute("data-log-type") as
    | "preview"
    | "full"
    | null;

  if (logType === "preview") {
    // Stop preview compilation
    console.log("[Writer] Stopping preview compilation from log toolbar");
    const statusLamp = (window as any).statusLamp;
    if (statusLamp) {
      statusLamp.setPreviewStatus("idle");
    }
  } else if (logType === "full") {
    // Stop full compilation
    console.log("[Writer] Stopping full compilation from log toolbar");
    const statusLamp = (window as any).statusLamp;
    if (statusLamp) {
      statusLamp.setFullCompileStatus("idle");
    }
  }
}

/**
 * Handle compilation log Close button
 * Closes the log panel
 */
export function handleCompilationLogClose(): void {
  const output = document.getElementById("compilation-output");
  if (output) {
    output.style.display = "none";
    console.log("[Writer] Compilation log panel closed");
  }
}

/**
 * Toggle compilation details panel
 */
export function toggleCompilationDetails(): void {
  const output = document.getElementById("compilation-output");
  const slimProgress = document.getElementById("compilation-slim-progress");

  if (!output) return;

  const isVisible = output.style.display === "block";

  if (isVisible) {
    // Hide details (slim progress disabled - status lamp provides feedback)
    output.style.display = "none";
  } else {
    // Show full details
    output.style.display = "block";
    if (slimProgress) {
      slimProgress.style.display = "none";
    }
  }
}
