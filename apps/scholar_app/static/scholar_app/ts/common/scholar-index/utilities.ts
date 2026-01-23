/**
 * Utility Functions
 * Helper functions for CSRF tokens, cookies, and toast notifications
 */

export function getCsrfToken(): string {
  const token = getCookie("csrftoken");
  if (!token) {
    console.warn("CSRF token not found");
    return "";
  }
  return token;
}

export function getCookie(name: string): string | null {
  let cookieValue: string | null = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export function showToast(message: string, type: string = "info"): void {
  const toast = document.createElement("div");
  toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  toast.style.cssText =
    "top: 20px; right: 20px; z-index: 1050; min-width: 300px;";
  toast.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;

  document.body.appendChild(toast);

  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
    }
  }, 3000);
}

// Export to global scope for backward compatibility
if (typeof window !== 'undefined') {
  (window as any).getCookie = getCookie;
  (window as any).showToast = showToast;
}
