/**
 * UI Utilities Module
 *
 * Provides shared UI utilities for alerts, form management, and helper functions.
 *
 * @module ui-utils
 */

/**
 * Alert type
 */
export type AlertType = "success" | "error" | "warning" | "info";

/**
 * Show alert banner at top of page
 */
export function showAlert(
  message: string,
  type: AlertType = "success",
): void {
  // Remove any existing alerts
  const existingAlerts = document.querySelectorAll(".scholar-alert");
  existingAlerts.forEach((alert) => alert.remove());

  // Create alert element
  const alert = document.createElement("div");
  alert.className = `scholar-alert scholar-alert-${type}`;
  alert.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10000;
        background: ${getAlertColor(type)};
        color: white;
        padding: 1rem 2rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        gap: 1rem;
        min-width: 300px;
        max-width: 600px;
        animation: slideDown 0.3s ease-out;
    `;

  const icon = getAlertIcon(type);

  alert.innerHTML = `
        <i class="fas fa-${icon}" style="font-size: 1.5rem; flex-shrink: 0;"></i>
        <div style="flex: 1; line-height: 1.6;">${message}</div>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; padding: 0; line-height: 1; flex-shrink: 0;">
            <i class="fas fa-times"></i>
        </button>
    `;

  // Add animation keyframes if not already added
  ensureAnimationStyles();

  document.body.appendChild(alert);
}

/**
 * Get alert color based on type
 */
function getAlertColor(type: AlertType): string {
  const colors: Record<AlertType, string> = {
    success: "var(--success-color)",
    error: "var(--error-color)",
    warning: "var(--warning-color)",
    info: "var(--info-color)",
  };
  return colors[type];
}

/**
 * Get alert icon based on type
 */
function getAlertIcon(type: AlertType): string {
  const icons: Record<AlertType, string> = {
    success: "check-circle",
    error: "times-circle",
    warning: "exclamation-triangle",
    info: "info-circle",
  };
  return icons[type];
}

/**
 * Ensure animation styles are added to document
 */
function ensureAnimationStyles(): void {
  if (!document.getElementById("alert-animation-styles")) {
    const style = document.createElement("style");
    style.id = "alert-animation-styles";
    style.textContent = `
            @keyframes slideDown {
                from {
                    transform: translateX(-50%) translateY(-100px);
                    opacity: 0;
                }
                to {
                    transform: translateX(-50%) translateY(0);
                    opacity: 1;
                }
            }
        `;
    document.head.appendChild(style);
  }
}

/**
 * Reset BibTeX form to initial state
 */
export function resetBibtexForm(): void {
  const formArea = document.getElementById("bibtexFormArea");
  const progressArea = document.getElementById("bibtexProgressArea");
  const form = document.getElementById(
    "bibtexEnrichmentForm",
  ) as HTMLFormElement | null;

  if (formArea) formArea.style.display = "block";
  if (progressArea) progressArea.style.display = "none";
  if (form) form.reset();
}

/**
 * Get CSRF token from page
 */
export function getCsrfToken(): string | null {
  const token = (
    document.querySelector("[name=csrfmiddlewaretoken]") as HTMLInputElement
  )?.value;
  return token || null;
}

/**
 * Update element text content safely
 */
export function updateElementText(
  elementId: string,
  text: string,
): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = text;
  }
}

/**
 * Update element HTML safely
 */
export function updateElementHTML(
  elementId: string,
  html: string,
): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = html;
  }
}

/**
 * Show/hide element
 */
export function setElementVisibility(
  elementId: string,
  visible: boolean,
): void {
  const element = document.getElementById(elementId);
  if (element) {
    if (visible) {
      element.classList.remove("hidden");
      element.style.display = "block";
    } else {
      element.classList.add("hidden");
      element.style.display = "none";
    }
  }
}

/**
 * Enable/disable button
 */
export function setButtonState(
  buttonId: string,
  enabled: boolean,
  opacity?: string,
): void {
  const button = document.getElementById(buttonId) as HTMLButtonElement | null;
  if (button) {
    button.disabled = !enabled;
    if (opacity !== undefined) {
      button.style.opacity = opacity;
    } else {
      button.style.opacity = enabled ? "1" : "0.5";
    }
    if (enabled) {
      button.classList.remove("disabled");
      button.style.cursor = "pointer";
    } else {
      button.classList.add("disabled");
      button.style.cursor = "not-allowed";
    }
  }
}

/**
 * Scroll element to bottom
 */
export function scrollToBottom(elementId: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.scrollTop = element.scrollHeight;
  }
}

/**
 * Format file size in MB
 */
export function formatFileSize(bytes: number): string {
  return (bytes / (1024 * 1024)).toFixed(2);
}
