/**
 * The header visitor countdown must read the SERVER's lease, and must never
 * evict on its own arithmetic.
 *
 * WHY THIS TEST EXISTS. A prospective customer clicked "Enter as visitor",
 * paused about two minutes to read, and the browser navigated itself to
 * /visitor-expired/ claiming "Your 60-minute visitor session ended 1 minute
 * ago." Three numbers contradicted each other on one screen:
 *
 *     landing page text : "session ended 1 minute ago"
 *     header badge      : 58:10 remaining
 *     server heartbeat  : remaining_seconds = 3599
 *
 * THE MECHANISM. header.ts captured `expiresAt` ONCE from a render-time
 * `data-expires-at` attribute and never refreshed it, then hard-navigated when
 * its own subtraction reached zero. That attribute carries the PROBATION
 * deadline: allocation grants only `PoolAllocator.PROBATION_SECONDS = 120`
 * (pool_manager.py:67,315) and the FIRST heartbeat promotes it to the full
 * hour (`extend_session_on_activity`, pool_manager.py:189-207). The stamp was
 * therefore never the lease, and the client evicted on it anyway.
 *
 * DO NOT "FIX" THIS BY DELETING PROBATION. PROBATION_SECONDS is deliberate
 * anti-crawler defence added after the 2026-07-14 slot-squatting incident,
 * where a JS-less crawler held all 16 slots for an hour each and every human
 * was served read-only. Probation is not the bug; treating the probation stamp
 * as the session deadline was.
 *
 * TWO-SIDED BY DESIGN. "Does not navigate" is a negative assertion that a
 * deleted function satisfies perfectly — so the eviction row below proves a
 * server-declared expiry STILL reaches /visitor-expired/.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { initVisitorCountdown } from "@shared/components/visitor-countdown";
import {
  getVisitorLease,
  registerVisitorLeaseVerifier,
  resetVisitorLeaseStore,
} from "@shared/utils/visitor-session-lease";
import { VisitorHeartbeat } from "@shared/utils/visitor-heartbeat";

/** The exact 200 body apps/infra/public_app/views/status/visitor.py:346-352 emits. */
function activeHeartbeat(expiresAt: Date, remainingSeconds: number): Response {
  return new Response(
    JSON.stringify({
      status: "active",
      remaining_seconds: remainingSeconds,
      expires_at: expiresAt.toISOString(),
    }),
    { status: 200, headers: { "content-type": "application/json" } },
  );
}

/** The exact 404 body visitor.py:354-357 emits when the allocation is gone. */
function expiredHeartbeat(): Response {
  return new Response(
    JSON.stringify({ error: "Allocation not found", status: "expired" }),
    { status: 404, headers: { "content-type": "application/json" } },
  );
}

/**
 * The header markup a visitor gets, per
 * templates/global_base_partials/global_header.html:411-412,450-454.
 * `expiresAt` is the render-time attribute — i.e. the probation stamp.
 */
function renderVisitorHeader(expiresAt: Date): HTMLElement {
  const toggle = document.createElement("button");
  toggle.id = "visitor-menu-toggle";
  toggle.dataset.expiresAt = expiresAt.toISOString();
  document.body.appendChild(toggle);

  const countdown = document.createElement("span");
  countdown.id = "visitor-countdown";
  countdown.textContent = "⏰ --:--";
  document.body.appendChild(countdown);

  document.body.dataset.userType = "visitor";
  return countdown;
}

/**
 * Let the in-flight heartbeat finish without moving the clock.
 *
 * `Response.json()` resolves through undici's body stream, which schedules on
 * the immediate queue — and the immediate queue is faked here. Awaiting bare
 * microtasks is therefore NOT enough: it leaves the response unread, the test
 * asserts against a countdown that never got its lease, and the next test then
 * fails with "Body has already been read". `advanceTimersByTimeAsync(0)` drains
 * the due timers AND the microtasks at the current instant.
 */
async function settleHeartbeat(): Promise<void> {
  for (let i = 0; i < 5; i++) await vi.advanceTimersByTimeAsync(0);
}

const BASE_TIME = new Date("2026-08-18T09:00:00.000Z");
const PROBATION_SECONDS = 120; // mirrors PoolAllocator.PROBATION_SECONDS
const FULL_SESSION_SECONDS = 3600;

describe("header visitor countdown", () => {
  let replaceSpy: ReturnType<typeof vi.fn>;
  let assignSpy: ReturnType<typeof vi.fn>;
  let reloadSpy: ReturnType<typeof vi.fn>;
  let nativeFetch: typeof window.fetch;
  let heartbeat: VisitorHeartbeat | null;
  let countdownHandle: { refresh(): void; stop(): void } | null;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(BASE_TIME);

    document.body.innerHTML = "";
    delete document.body.dataset.userType;
    resetVisitorLeaseStore();

    nativeFetch = window.fetch;
    heartbeat = null;
    countdownHandle = null;

    replaceSpy = vi.fn();
    assignSpy = vi.fn();
    reloadSpy = vi.fn();
    // jsdom's window.location is not configurable in the normal way; replace
    // the whole object so ANY navigation attempt is captured, not performed.
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: {
        href: "https://scitex.ai/",
        pathname: "/",
        replace: replaceSpy,
        assign: assignSpy,
        reload: reloadSpy,
      },
    });
  });

  afterEach(() => {
    countdownHandle?.stop();
    heartbeat?.destroy();
    window.fetch = nativeFetch;
    resetVisitorLeaseStore();
    document.body.innerHTML = "";
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // --- ROW 1: THE FIX BINDS ------------------------------------------------

  it("keeps an extended session alive past the render-time probation stamp", async () => {
    // Arrange -- the exact production shape. The page was rendered with the
    // 120s probation stamp; the server has since promoted the lease to a full
    // hour, and says so on every heartbeat.
    const probationStamp = new Date(
      BASE_TIME.getTime() + PROBATION_SECONDS * 1000,
    );
    const realLease = new Date(
      BASE_TIME.getTime() + FULL_SESSION_SECONDS * 1000,
    );
    const countdown = renderVisitorHeader(probationStamp);
    window.fetch = vi
      .fn()
      .mockImplementation(async () =>
        activeHeartbeat(realLease, FULL_SESSION_SECONDS - 1),
      );

    // Act -- heartbeat first (it is what publishes the lease), then the
    // countdown, then the visitor spends two and a half minutes reading.
    heartbeat = new VisitorHeartbeat();
    await settleHeartbeat();
    countdownHandle = initVisitorCountdown();
    vi.setSystemTime(new Date(BASE_TIME.getTime() + 150 * 1000));
    countdownHandle!.refresh();

    // Assert -- the whole bug in three lines: the stamp has passed, and
    // nothing evicts.
    expect(Date.now()).toBeGreaterThan(probationStamp.getTime());
    expect(replaceSpy).not.toHaveBeenCalled();
    expect(assignSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
    // ...and the badge shows the REAL remaining time, not "EXPIRED".
    expect(countdown.textContent).toBe("⏰ 57:30");
  });

  it("takes its deadline from the heartbeat, not from the render attribute", async () => {
    // Arrange
    const probationStamp = new Date(
      BASE_TIME.getTime() + PROBATION_SECONDS * 1000,
    );
    const realLease = new Date(
      BASE_TIME.getTime() + FULL_SESSION_SECONDS * 1000,
    );
    renderVisitorHeader(probationStamp);
    window.fetch = vi
      .fn()
      .mockImplementation(async () =>
        activeHeartbeat(realLease, FULL_SESSION_SECONDS - 1),
      );

    // Act
    heartbeat = new VisitorHeartbeat();
    await settleHeartbeat();
    countdownHandle = initVisitorCountdown();

    // Assert -- provenance, so a future "seed it again on every render" change
    // is caught rather than silently re-introducing the bug.
    const lease = getVisitorLease();
    expect(lease.source).toBe("heartbeat");
    expect(lease.expiresAt!.toISOString()).toBe(realLease.toISOString());
  });

  // --- ROW 2: THE EVICTION STILL WORKS -------------------------------------

  it("still reaches /visitor-expired/ when the SERVER reports the session gone", async () => {
    // Arrange -- a lease that has not run out on the client's own clock, so
    // the ONLY thing that can evict here is the server's word.
    const realLease = new Date(
      BASE_TIME.getTime() + FULL_SESSION_SECONDS * 1000,
    );
    const countdown = renderVisitorHeader(realLease);
    window.fetch = vi.fn().mockImplementation(async () => expiredHeartbeat());

    // Act
    heartbeat = new VisitorHeartbeat();
    countdownHandle = initVisitorCountdown();
    await settleHeartbeat();

    // Assert -- this is the row a careless fix fails: deleting the eviction
    // path passes every "does not navigate" assertion above.
    expect(replaceSpy).toHaveBeenCalledWith("/visitor-expired/");
    expect(getVisitorLease().serverExpired).toBe(true);
    // It must also SAY so before leaving.
    expect(countdown.textContent).toBe("⏰ EXPIRED");
  });

  it("does not evict twice, and does not evict off the expired page itself", async () => {
    // Arrange -- landing on /visitor-expired/ and bouncing again is the loop
    // that a previous version of this code produced.
    (window.location as unknown as { pathname: string }).pathname =
      "/visitor-expired/";
    renderVisitorHeader(new Date(BASE_TIME.getTime() + 60 * 1000));
    window.fetch = vi.fn().mockImplementation(async () => expiredHeartbeat());

    // Act
    heartbeat = new VisitorHeartbeat();
    await settleHeartbeat();

    // Assert
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  // --- THE CLIENT'S OWN ZERO IS NOT A VERDICT ------------------------------

  it("asks the server instead of navigating when its own countdown hits zero", () => {
    // Arrange -- a stale stamp already in the past and no heartbeat yet. This
    // is a laptop resumed from sleep, a drifting clock, or simply the
    // probation stamp: exactly the states that used to evict.
    const staleStamp = new Date(BASE_TIME.getTime() - 5 * 1000);
    const countdown = renderVisitorHeader(staleStamp);
    const verifier = vi.fn();
    registerVisitorLeaseVerifier(verifier);

    // Act
    countdownHandle = initVisitorCountdown();

    // Assert -- it renders the belief, and asks rather than acts.
    expect(countdown.textContent).toBe("⏰ EXPIRED");
    expect(replaceSpy).not.toHaveBeenCalled();
    expect(verifier).toHaveBeenCalledTimes(1);
  });

  it("recovers when the verification comes back with a live lease", async () => {
    // Arrange -- the resumed-laptop case end to end, through the real
    // heartbeat client: the countdown believes it is over, the server does not.
    const staleStamp = new Date(BASE_TIME.getTime() - 5 * 1000);
    const realLease = new Date(
      BASE_TIME.getTime() + FULL_SESSION_SECONDS * 1000,
    );
    const countdown = renderVisitorHeader(staleStamp);
    window.fetch = vi
      .fn()
      .mockImplementation(async () =>
        activeHeartbeat(realLease, FULL_SESSION_SECONDS - 1),
      );
    heartbeat = new VisitorHeartbeat();

    // Act
    countdownHandle = initVisitorCountdown();
    expect(countdown.textContent).toBe("⏰ EXPIRED"); // believed, not acted on
    await settleHeartbeat();
    countdownHandle!.refresh();

    // Assert
    expect(replaceSpy).not.toHaveBeenCalled();
    // The full hour the server granted — the clock has not moved, only the
    // client's belief about the deadline has.
    expect(countdown.textContent).toBe("⏰ 1:00:00");
  });

  it("does not flood the endpoint while parked at zero", async () => {
    // Arrange -- the countdown ticks every second; without throttling, a stuck
    // zero would be 60 heartbeat requests a minute.
    const staleStamp = new Date(BASE_TIME.getTime() - 5 * 1000);
    renderVisitorHeader(staleStamp);
    const verifier = vi.fn();
    registerVisitorLeaseVerifier(verifier);

    // Act -- ten seconds of ticking.
    countdownHandle = initVisitorCountdown();
    await vi.advanceTimersByTimeAsync(10_000);

    // Assert
    expect(verifier).toHaveBeenCalledTimes(1);
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  it("does not beat on behalf of a visitor who has walked away", async () => {
    // Arrange -- an abandoned tab. A verification beat EXTENDS the lease
    // server-side, so answering the countdown here would resurrect a dead
    // session and hold its pool slot for another hour — the very squatting
    // probation and the idle reaper exist to prevent.
    const lease = new Date(BASE_TIME.getTime() + 30 * 1000);
    const countdown = renderVisitorHeader(lease);
    window.fetch = vi
      .fn()
      .mockImplementation(async () =>
        activeHeartbeat(lease, FULL_SESSION_SECONDS - 1),
      );
    heartbeat = new VisitorHeartbeat();
    await settleHeartbeat();
    const beatsWhilePresent = (window.fetch as ReturnType<typeof vi.fn>).mock
      .calls.length;

    // Act -- five minutes pass with no mouse, key or scroll event at all, and
    // the lease runs out.
    countdownHandle = initVisitorCountdown();
    vi.setSystemTime(new Date(BASE_TIME.getTime() + 5 * 60 * 1000));
    countdownHandle!.refresh();
    await settleHeartbeat();

    // Assert -- the countdown DID reach zero (so the row is not passing
    // vacuously on a branch that never ran)...
    expect(countdown.textContent).toBe("⏰ EXPIRED");
    // ...and it stayed silent rather than beating. When they return,
    // onActivity() sends a real heartbeat and the server's answer decides.
    expect((window.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(
      beatsWhilePresent,
    );
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  // --- IT STILL HAS TO DO ITS JOB ------------------------------------------

  it("renders the remaining time every second", async () => {
    // Arrange -- without this, every negative assertion above passes for free
    // on a countdown that was deleted or that returns early.
    const lease = new Date(BASE_TIME.getTime() + 10 * 60 * 1000);
    const countdown = renderVisitorHeader(lease);

    // Act
    countdownHandle = initVisitorCountdown();
    expect(countdown.textContent).toBe("⏰ 10:00");
    await vi.advanceTimersByTimeAsync(3000);

    // Assert
    expect(countdown.textContent).toBe("⏰ 09:57");
  });

  it("does not start when there is no visitor badge", () => {
    // Arrange -- signed-in users and anonymous landing visitors.
    // Act
    countdownHandle = initVisitorCountdown();
    // Assert
    expect(countdownHandle).toBeNull();
  });

  it("does not start a second timer when the inline fallback is already ticking", () => {
    // Arrange -- global_header.html:568-623 runs a no-bundle fallback and
    // marks the toggle; two timers would double-paint.
    const countdown = renderVisitorHeader(
      new Date(BASE_TIME.getTime() + 10 * 60 * 1000),
    );
    document
      .getElementById("visitor-menu-toggle")!
      .setAttribute("data-inline-countdown", "true");

    // Act
    countdownHandle = initVisitorCountdown();

    // Assert
    expect(countdownHandle).toBeNull();
    expect(countdown.textContent).toBe("⏰ --:--");
  });

  // --- CONTROL -------------------------------------------------------------

  it("CONTROL: the navigation spies do capture a call when one is made", () => {
    // Arrange -- every "does not navigate" assertion is negative and passes
    // for free if the spy is not wired to the object under test.
    // Act
    window.location.replace("/visitor-expired/");
    // Assert
    expect(replaceSpy).toHaveBeenCalledWith("/visitor-expired/");
  });
});
