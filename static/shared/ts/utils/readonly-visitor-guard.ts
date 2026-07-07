/**
 * Read-only visitor write guard (card hub-visitor-ux-allapps).
 *
 * Fail-loud UX: readonly visitors can VIEW everything; when a WRITE
 * attempt is rejected, the backend answers with a structured 403
 * (`{ reason: "readonly-visitor", ... }` — see
 * apps/infra/project_app/services/visitor_pool/session_role.py).
 * This module intercepts those responses in the shared fetch layer and
 * renders ONE actionable toast: Sign up / Log in / retry later.
 *
 * Page rendering is never blocked — only the toast reacts to writes.
 */

const READONLY_REASON = "readonly-visitor";
const TOAST_ID = "readonly-visitor-toast";

interface ReadonlyRejection {
  reason?: string;
  error?: string;
  detail?: string;
  signup_url?: string;
  login_url?: string;
}

/** Render the actionable read-only toast (single instance). */
export function showReadonlyVisitorToast(
  payload: ReadonlyRejection = {},
): void {
  // One toast at a time — repeated rejected writes must not stack.
  if (document.getElementById(TOAST_ID)) return;

  const signupUrl = payload.signup_url || "/auth/signup/";
  const loginUrl =
    payload.login_url ||
    `/auth/login/?next=${encodeURIComponent(window.location.pathname)}`;
  const detail =
    payload.detail || "Visitor pool is full — you are browsing read-only.";

  const toast = document.createElement("div");
  toast.id = TOAST_ID;
  toast.setAttribute("role", "alert");
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    max-width: 360px;
    padding: 14px 16px;
    border-radius: 10px;
    background: var(--workspace-bg-secondary, #2a2a33);
    color: var(--workspace-text-primary, #e8e8ee);
    border: 1px solid var(--workspace-border-default, #44444f);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
    font-size: 13px;
    line-height: 1.5;
  `;

  const text = document.createElement("div");
  text.style.marginBottom = "10px";
  const title = document.createElement("strong");
  title.textContent = "Read-only session";
  const body = document.createElement("div");
  body.textContent = detail;
  text.appendChild(title);
  text.appendChild(body);

  const actions = document.createElement("div");
  actions.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;";

  const btnBase = `
    display:inline-block;padding:6px 12px;border-radius:7px;
    font-size:12.5px;font-weight:600;text-decoration:none;cursor:pointer;
    border:1px solid var(--workspace-border-default, #44444f);
  `;

  const signup = document.createElement("a");
  signup.href = signupUrl;
  signup.textContent = "Sign up";
  signup.style.cssText =
    btnBase +
    "background: var(--app-accent-hub, #6a5a8a); border-color: var(--app-accent-hub, #6a5a8a); color:#fff;";

  const login = document.createElement("a");
  login.href = loginUrl;
  login.textContent = "Log in";
  login.style.cssText =
    btnBase + "color: var(--workspace-text-primary, #e8e8ee);";

  const retry = document.createElement("button");
  retry.type = "button";
  retry.textContent = "Retry later";
  retry.style.cssText =
    btnBase +
    "background:transparent;color: var(--workspace-text-muted, #9a9aa8);";
  retry.addEventListener("click", () => toast.remove());

  actions.appendChild(signup);
  actions.appendChild(login);
  actions.appendChild(retry);

  toast.appendChild(text);
  toast.appendChild(actions);
  document.body.appendChild(toast);
}

/** True when a 403 response carries the structured readonly rejection. */
async function isReadonlyRejection(
  response: Response,
): Promise<ReadonlyRejection | null> {
  if (response.status !== 403) return null;
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  try {
    const data = (await response.clone().json()) as ReadonlyRejection;
    return data && data.reason === READONLY_REASON ? data : null;
  } catch {
    // 403 without a JSON body — not ours; leave it to the caller.
    return null;
  }
}

/**
 * Patch window.fetch so EVERY app's write rejection surfaces the toast —
 * no per-call-site wiring. The original response is returned untouched,
 * so existing error handling keeps working.
 */
export function installReadonlyVisitorGuard(): void {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const response = await nativeFetch(input, init);
    try {
      const rejection = await isReadonlyRejection(response);
      if (rejection) showReadonlyVisitorToast(rejection);
    } catch {
      // Guard must never break the caller's request flow.
    }
    return response;
  };
}

// Auto-install for readonly sessions only (body[data-session-role] is set
// by global_base.html from the canonical backend session-role model).
function autoInstall(): void {
  if (document.body.dataset.sessionRole === "readonly_visitor") {
    installReadonlyVisitorGuard();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", autoInstall);
} else {
  autoInstall();
}

// EOF
