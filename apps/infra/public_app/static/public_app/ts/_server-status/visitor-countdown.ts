/**
 * Visitor Pool Countdown Timers -- DISPLAY ONLY. Never navigate from here.
 *
 * WHY. This function iterates EVERY `.slot-time-remaining` element on
 * /server-status/ -- all 16 slot cards, other visitors' included -- and each
 * card's `data-expires` is a RENDER-TIME SNAPSHOT baked into the HTML by
 * server_status.html. Nothing re-renders those cards: the metrics updater
 * rewrites only the `#*CurrentValue` ids and the chart panels only redraw SVG.
 * So the timestamps here go stale by construction, and they are stale in a
 * specific, guaranteed way:
 *
 *   PoolAllocator.allocate() grants a PROBATION lease of only 120 seconds
 *   (pool_manager.py:67,317). The visitor's FIRST heartbeat then promotes it
 *   server-side to SESSION_LIFETIME_HOURS = 1 hour
 *   (pool_manager.py:49,203 extend_session_on_activity).
 *
 * A freshly-arrived visitor therefore always holds a card claiming 0-120s
 * while the authoritative database lease is a full hour. It reads as
 * "Expires in 1 min" on a brand-new session -- which is a display artefact of
 * probation, not a short session.
 *
 * Until 2026-08-04 this branch called `window.location.replace()`, so the
 * countdown evicted visitors whose sessions were alive in the database, and
 * /visitor-expired/ clears the session and allocates a new one -- a fresh
 * 120s probation card -- closing the loop. The operator hit it repeatedly;
 * nginx recorded four cycles in five minutes, at 1s, 9s, 26s and 34s after
 * load, with every heartbeat and status poll returning 200 throughout. The
 * server never expired anything. The page evicted itself.
 *
 * Note the comment that used to sit on that line: "prevents infinite reload
 * loop". An earlier loop was fixed by swapping a reload for a redirect, which
 * created this loop. The lesson is not "use replace() instead of reload()" --
 * it is that a countdown rendering someone else's lease, from data it cannot
 * refresh, has no business deciding anything.
 *
 * THE AUTHORITATIVE EXPIRY SIGNAL IS THE HEARTBEAT, and it already exists:
 * static/shared/ts/utils/visitor-heartbeat.ts:103 navigates to
 * /visitor-expired/ when the server answers 401/404, i.e. when the session is
 * genuinely gone. It polls every 30s, so real expiry is still caught -- just
 * by the component that actually knows, within one poll.
 */

export function updateVisitorCountdowns(): void {
  document
    .querySelectorAll(".slot-time-remaining")
    .forEach((element: Element) => {
      const expiresAt = (element as HTMLElement).dataset.expires;
      if (!expiresAt) return;

      const span = element.querySelector("span");
      if (!span) return;

      const now = new Date();
      const expires = new Date(expiresAt);
      const remainingMs = expires.getTime() - now.getTime();
      const remainingSeconds = Math.max(0, Math.floor(remainingMs / 1000));
      const remainingMinutes = Math.floor(remainingSeconds / 60);

      if (remainingSeconds > 0) {
        span.textContent = `Expires in ${remainingMinutes} min`;
      } else {
        // DISPLAY ONLY. This must never navigate -- see the file docstring.
        span.textContent = "Expired";
      }
    });
}
