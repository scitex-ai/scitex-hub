/**
 * Analytics Utility Module
 * Centralized Google Analytics 4 event tracking for SciTeX modules
 *
 * Privacy-conscious: Only tracks module usage counts, never content or PII
 */

// Module categories for consistent naming
export type ModuleCategory =
  | "files"
  | "scholar"
  | "code"
  | "vis"
  | "writer"
  | "tools"
  | "explore"
  | "server_status"
  | "auth"
  | "settings";

// Event types for each module
export type ModuleEvent =
  // Page views
  | "module_view"
  // Files actions
  | "file_upload"
  | "file_download"
  | "folder_create"
  // Scholar actions
  | "paper_search"
  | "paper_save"
  | "citation_export"
  // Code actions
  | "code_run"
  | "code_save"
  | "terminal_open"
  // Vis actions
  | "chart_create"
  | "chart_export"
  // Writer actions
  | "document_create"
  | "document_export"
  // Tools actions
  | "tool_use"
  // Auth actions
  | "sign_up"
  | "sign_in"
  | "email_verified";

declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
  }
}

/**
 * Check if Google Analytics is available
 */
function isGtagAvailable(): boolean {
  return typeof window !== "undefined" && typeof window.gtag === "function";
}

/**
 * Track a generic event to Google Analytics
 * @param eventName - The event name (e.g., 'module_view', 'file_upload')
 * @param category - The module category (e.g., 'files', 'scholar')
 * @param label - Optional label for additional context (avoid PII)
 */
export function trackEvent(
  eventName: ModuleEvent | string,
  category: ModuleCategory | string,
  label?: string
): void {
  if (!isGtagAvailable()) {
    return;
  }

  const params: Record<string, string> = {
    event_category: category,
  };

  if (label) {
    params.event_label = label;
  }

  window.gtag!("event", eventName, params);
}

/**
 * Track module page view
 * Call this when a user navigates to a module
 * @param module - The module being viewed
 */
export function trackModuleView(module: ModuleCategory): void {
  trackEvent("module_view", module);
}

/**
 * Track file operations (without file names for privacy)
 */
export function trackFileOperation(
  operation: "file_upload" | "file_download" | "folder_create"
): void {
  trackEvent(operation, "files");
}

/**
 * Track scholar actions (without search queries for privacy)
 */
export function trackScholarAction(
  action: "paper_search" | "paper_save" | "citation_export"
): void {
  trackEvent(action, "scholar");
}

/**
 * Track code actions
 */
export function trackCodeAction(
  action: "code_run" | "code_save" | "terminal_open"
): void {
  trackEvent(action, "code");
}

/**
 * Track visualization actions
 */
export function trackVisAction(action: "chart_create" | "chart_export"): void {
  trackEvent(action, "vis");
}

/**
 * Track writer actions
 */
export function trackWriterAction(
  action: "document_create" | "document_export"
): void {
  trackEvent(action, "writer");
}

/**
 * Track tool usage (with tool type, not user content)
 * @param toolType - Generic tool type (e.g., 'converter', 'formatter')
 */
export function trackToolUse(toolType: string): void {
  trackEvent("tool_use", "tools", toolType);
}

/**
 * Auto-track module view on page load
 * Add data-track-module="module_name" to body or main container
 */
export function initAutoTracking(): void {
  if (typeof document === "undefined") return;

  document.addEventListener("DOMContentLoaded", () => {
    const trackElement = document.querySelector("[data-track-module]");
    if (trackElement) {
      const module = trackElement.getAttribute(
        "data-track-module"
      ) as ModuleCategory;
      if (module) {
        trackModuleView(module);
      }
    }
  });
}

// Auto-initialize tracking when module is imported
initAutoTracking();
