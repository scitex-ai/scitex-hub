/**
 * Header visitor countdown — DISPLAY ONLY.
 *
 * Extracted from header.ts so it can be tested; header.ts calls
 * `initVisitorCountdown()` where the inline block used to sit.
 *
 * TWO PROPERTIES THIS FILE MUST KEEP.
 *
 *  1. The deadline comes from the shared lease
 *     (static/shared/ts/utils/visitor-session-lease.ts), which every heartbeat
 *     response refreshes. The render-time `data-expires-at` attribute is only
 *     a provisional seed — it carries the 120s PROBATION stamp, not the
 *     session lease, so trusting it for the whole session is what made an
 *     engaged visitor get thrown to /visitor-expired/ two minutes in while
 *     this very badge still read 58:10.
 *
 *  2. It NEVER navigates on its own arithmetic. Reaching zero paints
 *     "EXPIRED" and ASKS the server. The redirect happens only from
 *     `recordVisitorSessionExpired()`, i.e. only after the server answered
 *     404/401/403. A drifting clock or a laptop resumed from sleep must not
 *     be able to end somebody's session.
 *
 * The /server-status/ slot cards learned the same lesson separately — see
 * apps/infra/public_app/static/public_app/ts/_server-status/visitor-countdown.ts
 * and its test, which records two prior regressions of exactly this shape.
 */

import {
  getVisitorLease,
  requestVisitorLeaseVerification,
  seedVisitorLeaseFromRender,
  subscribeVisitorLease,
} from "../utils/visitor-session-lease";

const EXPIRED_COLOR = "#f44336";
const WARNING_COLOR = "#ff9800";
const URGENT_MS = 5 * 60 * 1000;
const WARNING_MS = 15 * 60 * 1000;

export interface VisitorCountdownHandle {
  /** Force a repaint (also used by the 1s tick). */
  refresh(): void;
  /** Stop ticking and unsubscribe. */
  stop(): void;
}

function paint(el: HTMLElement | null, text: string, color: string): void {
  if (!el) return;
  // The mobile hamburger entry renders bare digits; the others carry a clock.
  el.textContent = el.id === "mobile-visitor-countdown" ? text : `⏰ ${text}`;
  el.style.color = color;
}

function formatRemaining(timeLeftMs: number): string {
  const hours = Math.floor(timeLeftMs / (1000 * 60 * 60));
  const minutes = Math.floor((timeLeftMs % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((timeLeftMs % (1000 * 60)) / 1000);
  const mm = String(minutes).padStart(2, "0");
  const ss = String(seconds).padStart(2, "0");
  return hours > 0 ? `${hours}:${mm}:${ss}` : `${mm}:${ss}`;
}

/**
 * Wire the header countdown. Returns null when there is nothing to run
 * (no visitor badge, unparseable stamp, or the inline fallback already ticking).
 */
export function initVisitorCountdown(): VisitorCountdownHandle | null {
  const visitorMenuToggle = document.getElementById("visitor-menu-toggle");
  const mobileBadge = document.querySelector(
    ".header-visitor-badge-mobile",
  ) as HTMLElement | null;

  const expiresAtSource =
    (visitorMenuToggle && visitorMenuToggle.dataset.expiresAt) ||
    (mobileBadge && mobileBadge.dataset.expiresAt) ||
    null;

  if (!expiresAtSource) return null;

  if (!seedVisitorLeaseFromRender(expiresAtSource)) {
    // Only complain when nothing better is already known; a heartbeat lease
    // outranking the attribute is the normal, healthy case.
    if (getVisitorLease().expiresAt === null) {
      console.error(
        "[header] Invalid visitor expiration date:",
        expiresAtSource,
      );
      return null;
    }
  }

  if (visitorMenuToggle?.hasAttribute("data-inline-countdown")) {
    // The template's no-JS-bundle fallback is already ticking
    // (global_header.html:567-623); a second timer would double-paint.
    return null;
  }

  const targets: (HTMLElement | null)[] = [
    document.getElementById("visitor-countdown"),
    document.getElementById("mobile-visitor-countdown"),
    document.getElementById("mobile-header-visitor-countdown"),
  ];

  function showExpired(): void {
    targets.forEach((el) => paint(el, "EXPIRED", EXPIRED_COLOR));
  }

  function refresh(): void {
    const lease = getVisitorLease();

    if (lease.serverExpired) {
      // The server ended it. Say so; the navigation is owned by the lease.
      showExpired();
      return;
    }

    if (!lease.expiresAt) return;

    const timeLeft = lease.expiresAt.getTime() - Date.now();

    if (timeLeft <= 0) {
      // We BELIEVE it is over. We do not act on that belief — the render-time
      // stamp is a probation deadline and the clock may have drifted. Show it,
      // then ask the server; only its answer may evict.
      showExpired();
      requestVisitorLeaseVerification();
      return;
    }

    const timeString = formatRemaining(timeLeft);
    const color =
      timeLeft < URGENT_MS
        ? EXPIRED_COLOR
        : timeLeft < WARNING_MS
          ? WARNING_COLOR
          : "inherit";
    targets.forEach((el) => paint(el, timeString, color));
  }

  const unsubscribe = subscribeVisitorLease(refresh);
  refresh();
  const intervalId = window.setInterval(refresh, 1000);

  return {
    refresh,
    stop(): void {
      window.clearInterval(intervalId);
      unsubscribe();
    },
  };
}
