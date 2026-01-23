/**
 * Storage utilities for canvas tabs
 * Tabs are now derived from filesystem - localStorage is no longer used
 */

/**
 * Get CSRF token from cookie
 */
export function getCSRFToken(): string {
  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "csrftoken") {
      return value;
    }
  }
  return "";
}
