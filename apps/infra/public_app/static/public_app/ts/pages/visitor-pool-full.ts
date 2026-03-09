/**
 * Visitor Pool Full Page
 * Handles cookie acceptance for visitor slot allocation
 */

const CONSENT_COOKIE = "scitex_consent";
const CONSENT_KEY = "scitex_cookie_consent";

function setCookie(name: string, value: string, days: number): void {
  const expires = new Date();
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
}

function acceptCookiesAndRedirect(): void {
  // Set the consent cookie for server-side check
  setCookie(CONSENT_COOKIE, "1", 365);

  // Set localStorage for client-side cookie banner
  localStorage.setItem(
    CONSENT_KEY,
    JSON.stringify({
      accepted: true,
      version: "1",
      timestamp: Date.now(),
    })
  );

  // Redirect to homepage (middleware will allocate visitor)
  window.location.href = "/";
}

function initVisitorPoolFull(): void {
  const acceptBtn = document.getElementById("accept-cookies-btn");
  if (acceptBtn) {
    acceptBtn.addEventListener("click", acceptCookiesAndRedirect);
  }
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initVisitorPoolFull);
} else {
  initVisitorPoolFull();
}

export { initVisitorPoolFull };
