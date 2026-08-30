/**
 * Visitor Session Heartbeat
 *
 * Sends periodic heartbeats to the server while the user is active.
 * This allows the server to track idle time and manage session resources.
 *
 * It is also the ONLY thing on the page that knows when a visitor session is
 * really over, because it is the only thing that asks the server. Every
 * response is therefore published to the shared lease
 * (./visitor-session-lease), which the header countdown reads:
 *
 *   - 200 → `expires_at` becomes the countdown's deadline. The server extends
 *     the lease on every beat (`extend_session_on_activity`), and the first
 *     beat promotes the 120s probation stamp to the full hour — so this is the
 *     only place the real deadline is ever visible to the client.
 *   - 404 / 401 / 403 → the session is genuinely gone; the lease evicts.
 *
 * This module registers itself as the lease's VERIFIER, so a countdown that
 * believes it has hit zero can ask the server instead of navigating on its own
 * arithmetic.
 */

import { API_URLS } from "./api-urls";
import {
  recordVisitorLeaseFromHeartbeat,
  recordVisitorSessionExpired,
  registerVisitorLeaseVerifier,
} from "./visitor-session-lease";

const HEARTBEAT_INTERVAL_MS = 30000; // 30 seconds
const IDLE_THRESHOLD_MS = 60000; // 1 minute of no activity = idle

interface HeartbeatResponse {
  status: string;
  remaining_seconds: number;
  /** ISO-8601 deadline. The authoritative lease — see module docstring. */
  expires_at: string;
}

class VisitorHeartbeat {
  private intervalId: number | null = null;
  private lastActivity: number = Date.now();
  private isIdle: boolean = false;

  constructor() {
    // Don't run on visitor-expired page (prevents redirect loop)
    if (window.location.pathname.includes("visitor-expired")) {
      return;
    }

    // Only run for visitor users
    const isVisitor = document.body.dataset.userType === "visitor";
    if (!isVisitor) {
      return;
    }

    // The countdown asks US when it thinks time is up; only the server's
    // answer may end a session.
    registerVisitorLeaseVerifier(() => this.verifySession());

    this.setupActivityListeners();
    this.startHeartbeat();
  }

  private setupActivityListeners(): void {
    const events = ["mousemove", "keydown", "click", "scroll", "touchstart"];
    events.forEach((event) => {
      document.addEventListener(event, () => this.onActivity(), {
        passive: true,
      });
    });
  }

  private onActivity(): void {
    this.lastActivity = Date.now();
    if (this.isIdle) {
      this.isIdle = false;
      console.log("[Heartbeat] User became active");
      this.sendHeartbeat(); // Immediate heartbeat when becoming active
    }
  }

  private startHeartbeat(): void {
    // Send initial heartbeat
    this.sendHeartbeat();

    // Set up interval
    this.intervalId = window.setInterval(() => {
      const idleTime = Date.now() - this.lastActivity;

      if (idleTime > IDLE_THRESHOLD_MS) {
        if (!this.isIdle) {
          this.isIdle = true;
          console.log("[Heartbeat] User became idle");
        }
        // Skip heartbeat when idle to allow resource release
        return;
      }

      this.sendHeartbeat();
    }, HEARTBEAT_INTERVAL_MS);
  }

  /**
   * Answer the countdown's "is this session really over?" question.
   *
   * NOT an unconditional beat. A beat EXTENDS the lease server-side
   * (`extend_session_on_activity` also stamps `last_activity`), so beating on
   * behalf of somebody who is not there would resurrect an abandoned session
   * and hold its pool slot for another hour — precisely the squatting the
   * probation lease and the idle reaper exist to prevent. If nobody is at the
   * keyboard we stay quiet: the countdown just reads "EXPIRED" to an empty
   * room, and the moment the visitor comes back `onActivity()` fires a real
   * heartbeat whose answer decides.
   */
  private async verifySession(): Promise<void> {
    const idleTime = Date.now() - this.lastActivity;
    if (idleTime > IDLE_THRESHOLD_MS) return;
    await this.sendHeartbeat();
  }

  private async sendHeartbeat(): Promise<void> {
    try {
      const response = await fetch(API_URLS.visitor.heartbeat, {
        method: "GET",
        credentials: "same-origin",
      });

      if (response.ok) {
        const data: HeartbeatResponse = await response.json();

        // THE AUTHORITATIVE DEADLINE. Publish it before anything else: the
        // header countdown's only other source is a render-time attribute
        // carrying the 120s probation stamp, and acting on that stamp is what
        // used to evict readers two minutes into an hour-long session.
        recordVisitorLeaseFromHeartbeat(data.expires_at);

        console.log(
          `[Heartbeat] Session active, ${Math.floor(data.remaining_seconds / 60)} min remaining`,
        );

        // Warn user when session is about to expire (5 min warning)
        if (data.remaining_seconds <= 300 && data.remaining_seconds > 240) {
          this.showSessionWarning(data.remaining_seconds);
        }
      } else if (
        response.status === 404 ||
        response.status === 401 ||
        response.status === 403
      ) {
        // The SERVER says the session is over — 404 carries
        // {"status": "expired"} (public_app/views/status/visitor.py:354-357),
        // 401 means the visitor login is gone. This is the ONLY signal that
        // may evict; the lease owns the navigation so there is exactly one
        // place that does it.
        console.log(
          "[Heartbeat] Session expired, redirecting to visitor-expired",
        );
        this.destroy(); // Stop heartbeat before redirect
        recordVisitorSessionExpired();
      }
    } catch (error) {
      console.warn("[Heartbeat] Error:", error);
    }
  }

  private showSessionWarning(remainingSeconds: number): void {
    const minutes = Math.ceil(remainingSeconds / 60);
    // Check if warning already shown
    if (document.querySelector(".session-warning-toast")) {
      return;
    }

    const toast = document.createElement("div");
    toast.className = "session-warning-toast position-fixed";
    toast.style.cssText = [
      "bottom: 20px",
      "right: 20px",
      "z-index: 9999",
      "max-width: 350px",
      "padding: 14px 18px",
      "border-radius: 8px",
      "background: var(--bg-secondary, #1e1e2e)",
      "color: var(--text-primary, #e0e0e0)",
      "border: 1px solid var(--warning-color, #d4a87a)",
      "box-shadow: 0 4px 12px rgba(0,0,0,0.3)",
      "font-size: 13px",
      "line-height: 1.5",
    ].join("; ");
    toast.innerHTML = `
      <strong style="color: var(--warning-color, #d4a87a);">Session Expiring</strong><br>
      Your visitor session will expire in ${minutes} minutes.
      <a href="/signup/" style="color: var(--accent-primary, #4a9eff);">Create an account</a> for unlimited access.
    `;

    document.body.appendChild(toast);

    // Auto-remove after 30 seconds
    setTimeout(() => toast.remove(), 30000);
  }

  public destroy(): void {
    if (this.intervalId) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => new VisitorHeartbeat());
} else {
  new VisitorHeartbeat();
}

export { VisitorHeartbeat };
