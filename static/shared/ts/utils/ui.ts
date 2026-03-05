/**
 * UI Utility Module
 * Common UI interaction helpers
 */

export type ToastType = "success" | "error" | "warning" | "info";

/**
 * Show a toast notification
 */
export function showToast(
  message: string,
  type: ToastType = "info",
  duration: number = 5000,
): void {
  const toast = document.createElement("div");
  toast.className = `alert alert-${type === "error" ? "danger" : type} alert-dismissible fade show`;
  toast.setAttribute("role", "alert");
  toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;

  toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

  document.body.appendChild(toast);

  if (duration > 0) {
    setTimeout(() => {
      toast.remove();
    }, duration);
  }
}

/**
 * Show a status message in a specific container
 */
export function showStatus(
  message: string,
  type: ToastType,
  containerId?: string,
): void {
  const container = containerId
    ? document.getElementById(containerId)
    : document.body;
  if (!container) return;

  const status = document.createElement("div");
  status.className = `alert alert-${type === "error" ? "danger" : type}`;
  status.textContent = message;
  status.style.margin = "10px 0";

  if (containerId) {
    const existing = container.querySelector(".alert");
    if (existing) existing.remove();
    container.appendChild(status);
  } else {
    document.body.insertBefore(status, document.body.firstChild);
  }

  setTimeout(() => status.remove(), 5000);
}

/**
 * Disable/enable button with loading state
 */
export function setButtonLoading(
  button: HTMLElement,
  isLoading: boolean,
  loadingText: string = "Loading...",
): void {
  const originalText = button.textContent;
  const originalHTML = button.innerHTML;

  if (isLoading) {
    button.setAttribute("disabled", "true");
    button.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${loadingText}`;
  } else {
    button.removeAttribute("disabled");
    button.textContent = originalText;
    button.innerHTML = originalHTML;
  }
}

/**
 * Show/hide loading spinner
 */
export function showSpinner(containerId: string, show: boolean = true): void {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (show) {
    const spinner = document.createElement("div");
    spinner.className = "spinner-container";
    spinner.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        `;
    container.appendChild(spinner);
  } else {
    const spinner = container.querySelector(".spinner-container");
    if (spinner) spinner.remove();
  }
}

/**
 * Modal helper to show/hide modals
 */
export class Modal {
  private element: HTMLElement;
  private bootstrap?: any;

  constructor(elementId: string) {
    const el = document.getElementById(elementId);
    if (!el) {
      throw new Error(`Modal element with id "${elementId}" not found`);
    }
    this.element = el;

    // Try to get Bootstrap modal instance
    if ((window as any).bootstrap) {
      this.bootstrap = new (window as any).bootstrap.Modal(el);
    }
  }

  show(): void {
    if (this.bootstrap) {
      this.bootstrap.show();
    } else {
      this.element.setAttribute("style", "display: flex;");
    }
  }

  hide(): void {
    if (this.bootstrap) {
      this.bootstrap.hide();
    } else {
      this.element.setAttribute("style", "display: none;");
    }
  }

  toggle(): void {
    if (this.bootstrap) {
      this.bootstrap.toggle();
    } else {
      const isHidden = this.element.style.display === "none";
      this.element.style.display = isHidden ? "flex" : "none";
    }
  }
}

/**
 * Confirm dialog helper
 */
export function confirm(message: string): Promise<boolean> {
  return Promise.resolve(window.confirm(message));
}

/**
 * Debounce function calls
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function calls
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle: boolean = false;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}
