/**
 * Cookie Consent Banner
 * GDPR/CCPA compliant cookie notification
 * Sets both localStorage and cookie for server-side verification
 */

const CONSENT_KEY = "scitex_cookie_consent";
const CONSENT_COOKIE = "scitex_consent"; // Cookie for server-side check
const CONSENT_VERSION = "1"; // Increment to re-show banner after policy changes

interface ConsentData {
  accepted: boolean;
  version: string;
  timestamp: number;
}

function getConsent(): ConsentData | null {
  try {
    const data = localStorage.getItem(CONSENT_KEY);
    if (!data) return null;
    return JSON.parse(data) as ConsentData;
  } catch {
    return null;
  }
}

function setCookie(name: string, value: string, days: number): void {
  const expires = new Date();
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
}

function setConsent(accepted: boolean): void {
  const data: ConsentData = {
    accepted,
    version: CONSENT_VERSION,
    timestamp: Date.now(),
  };
  // Store in localStorage for client-side checks
  localStorage.setItem(CONSENT_KEY, JSON.stringify(data));
  // Set cookie for server-side middleware to verify consent
  // Both "accept all" and "essential only" set this - we need session cookies either way
  setCookie(CONSENT_COOKIE, "1", 365);
}

function showBanner(banner: HTMLElement): void {
  // Small delay for CSS transition
  requestAnimationFrame(() => {
    banner.classList.add("visible");
  });
}

function hideBanner(banner: HTMLElement): void {
  banner.classList.remove("visible");
  // Remove from DOM after transition
  setTimeout(() => {
    banner.classList.add("dismissed");
  }, 300);
}

function handleAccept(banner: HTMLElement): void {
  setConsent(true);
  hideBanner(banner);
  // Enable analytics if needed
  console.log("[Cookie Consent] Accepted");
}

function handleDecline(banner: HTMLElement): void {
  setConsent(false);
  hideBanner(banner);
  // Disable non-essential cookies
  console.log("[Cookie Consent] Declined - only essential cookies");
}

function initCookieConsent(): void {
  const banner = document.getElementById("cookie-consent-banner");
  if (!banner) return;

  const acceptBtn = document.getElementById("cookie-consent-accept");
  const declineBtn = document.getElementById("cookie-consent-decline");

  // Check existing consent
  const consent = getConsent();

  // Show banner if no consent or version changed
  if (!consent || consent.version !== CONSENT_VERSION) {
    showBanner(banner);
  } else {
    // Already consented, hide banner
    banner.classList.add("dismissed");
  }

  // Button handlers
  acceptBtn?.addEventListener("click", () => handleAccept(banner));
  declineBtn?.addEventListener("click", () => handleDecline(banner));
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initCookieConsent);
} else {
  initCookieConsent();
}

export { initCookieConsent, getConsent, setConsent };
