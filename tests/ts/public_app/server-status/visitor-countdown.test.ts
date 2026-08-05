/**
 * The /server-status/ visitor countdown must NEVER navigate.
 *
 * WHY THIS TEST EXISTS. On 2026-08-03 the operator hit a loop: open
 * /server-status/, get thrown to "Your Visitor Session Has Expired", land back,
 * repeat. nginx recorded four cycles in five minutes -- 1s, 9s, 26s and 34s
 * after load -- while every heartbeat and every status poll returned 200. The
 * server never expired anything. The page evicted itself.
 *
 * THE MECHANISM. `updateVisitorCountdowns()` iterates EVERY `.slot-time-remaining`
 * element -- all 16 slot cards, other visitors' included -- and each card's
 * `data-expires` is a render-time snapshot that nothing refreshes. Allocation
 * grants a PROBATION lease of 120s (pool_manager.py:67,317); the first heartbeat
 * promotes it server-side to a full hour (pool_manager.py:49,203). So a
 * brand-new visitor ALWAYS holds a card claiming 0-120s while the real lease is
 * an hour. When that stale countdown reached zero it called
 * `window.location.replace('/visitor-expired/')`, which clears the session and
 * allocates a fresh 120s probation card -- closing the loop.
 *
 * WHY THE OBVIOUS FIX IS WRONG, recorded so it is not "simplified" back. Scoping
 * the redirect to the current user's card does NOT fix this: the viewer's own
 * card is precisely the stale one. Only removing the navigation does.
 *
 * AND IT HAS REGRESSED ONCE ALREADY. The previous implementation was
 * `setTimeout(() => location.reload(), 1000)` -- also a loop. It was "fixed" by
 * swapping the reload for a redirect, i.e. by changing how it navigated rather
 * than by noticing that a display-only countdown should not navigate at all.
 * That is why this is a test and not a comment.
 *
 * THE AUTHORITATIVE SIGNAL LIVES ELSEWHERE and is unaffected:
 * static/shared/ts/utils/visitor-heartbeat.ts:103 redirects on a 401/404 from
 * the server, i.e. when the session is genuinely gone.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { updateVisitorCountdowns } from "@public_app/_server-status/visitor-countdown";

/** One slot card, shaped like server_status.html:672-689 emits it. */
function addSlot(expiresAt: string | null, label = "visitor-001"): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "slot-time-remaining";
  wrapper.dataset.slot = label;
  if (expiresAt !== null) {
    wrapper.dataset.expires = expiresAt;
  }
  wrapper.appendChild(document.createElement("span"));
  document.body.appendChild(wrapper);
  return wrapper;
}

function isoIn(seconds: number): string {
  return new Date(Date.now() + seconds * 1000).toISOString();
}

describe("updateVisitorCountdowns", () => {
  let replaceSpy: ReturnType<typeof vi.fn>;
  let assignSpy: ReturnType<typeof vi.fn>;
  let reloadSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    document.body.innerHTML = "";
    replaceSpy = vi.fn();
    assignSpy = vi.fn();
    reloadSpy = vi.fn();
    // jsdom's window.location is not configurable in the normal way; replace the
    // whole object so ANY navigation attempt is captured rather than performed.
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: {
        href: "https://scitex.ai/server-status/",
        pathname: "/server-status/",
        replace: replaceSpy,
        assign: assignSpy,
        reload: reloadSpy,
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  // --- THE REGRESSION GUARD ------------------------------------------------

  it("does not navigate when the viewer's own card has already expired", () => {
    // Arrange -- the exact production shape: a freshly-allocated visitor whose
    // card carries a stale 120s probation stamp that has since run out, while
    // the server-side lease is a full hour.
    addSlot(isoIn(-5), "visitor-004");

    // Act
    updateVisitorCountdowns();

    // Assert -- the whole bug in one line.
    expect(replaceSpy).not.toHaveBeenCalled();
    expect(assignSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it("does not navigate when SOMEBODY ELSE's card has expired", () => {
    // Arrange -- the viewer is healthy with 55 minutes left; an unrelated
    // visitor's slot is dead. Iterating every card is what turned another
    // visitor's expiry into this viewer's eviction.
    addSlot(isoIn(3300), "visitor-001");
    addSlot(isoIn(-1), "visitor-002");
    addSlot(isoIn(-90), "visitor-003");

    // Act
    updateVisitorCountdowns();

    // Assert
    expect(replaceSpy).not.toHaveBeenCalled();
    expect(assignSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  // --- IT STILL HAS TO DO ITS JOB -----------------------------------------
  // Without these, the guard above passes for free on a function that was
  // deleted or that returns early -- "does not navigate" is a negative
  // assertion and a no-op satisfies it perfectly.

  it("renders the remaining minutes for a live slot", () => {
    // Arrange -- 55.5 minutes, deliberately NOT a whole minute. The display
    // floors, so an exact 55*60 lands on the boundary and the few milliseconds
    // between building the timestamp and reading it flip the result to 54.
    // Sitting mid-minute makes the assertion depend on the logic rather than on
    // how fast the machine is.
    const slot = addSlot(isoIn(55 * 60 + 30));

    // Act
    updateVisitorCountdowns();

    // Assert
    expect(slot.querySelector("span")!.textContent).toBe("Expires in 55 min");
  });

  it("renders 'Expired' for a dead slot", () => {
    // Arrange
    const slot = addSlot(isoIn(-5));

    // Act
    updateVisitorCountdowns();

    // Assert -- it must still SAY so; the fix removes the navigation, not the
    // information.
    expect(slot.querySelector("span")!.textContent).toBe("Expired");
  });

  it("floors sub-minute leases to '0 min' rather than hiding them", () => {
    // Arrange -- this is why the operator saw "Expires in 1 min" on a session
    // that was actually an hour long: helpers.py floors int(seconds/60), and a
    // 120s probation lease reads as 1-2 min. Pinning the behaviour so the
    // display artefact is not mistaken for a lifetime bug again.
    const slot = addSlot(isoIn(45));

    // Act
    updateVisitorCountdowns();

    // Assert
    expect(slot.querySelector("span")!.textContent).toBe("Expires in 0 min");
  });

  it("ignores a card with no data-expires instead of throwing", () => {
    // Arrange -- FREE slots render without the attribute.
    const slot = addSlot(null);

    // Act
    updateVisitorCountdowns();

    // Assert
    expect(slot.querySelector("span")!.textContent).toBe("");
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  // --- CONTROL -------------------------------------------------------------

  it("CONTROL: the navigation spies do capture a call when one is made", () => {
    // Arrange -- every navigation assertion above is negative, and a negative
    // passes for free if the spy is not wired to the object under test. Prove
    // the spy would have caught the old behaviour.
    // Act
    window.location.replace("/visitor-expired/");
    // Assert
    expect(replaceSpy).toHaveBeenCalledWith("/visitor-expired/");
  });
});
