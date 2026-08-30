/**
 * Visitor Session Lease — the single client-side source of truth for WHEN the
 * current visitor session ends, and for WHO decided that it ended.
 *
 * WHY THIS EXISTS. A visitor clicked "Enter as visitor", read for two minutes,
 * and the browser navigated itself to /visitor-expired/ claiming the 60-minute
 * session had ended — while the header badge on that very page still showed
 * 58:10 remaining and the server heartbeat reported remaining_seconds = 3599.
 *
 * The header countdown captured `expiresAt` ONCE from a render-time
 * `data-expires-at` attribute and never refreshed it. That attribute carries
 * the PROBATION deadline, not the session lease: allocation grants only
 * `PoolAllocator.PROBATION_SECONDS = 120` (apps/infra/project_app/services/
 * visitor_pool/pool_manager.py:67,315) and the FIRST heartbeat promotes it to
 * the full hour (`extend_session_on_activity`, same file :188-207). So the
 * render-time stamp is, by construction, ~120 seconds — never the lease. The
 * client then evicted an engaged reader on a number that was never true.
 *
 * TWO RULES ENCODED HERE.
 *
 *  1. The lease is REFRESHED from every heartbeat response (`expires_at`), so
 *     the countdown tracks the server's actual deadline rather than a snapshot
 *     taken before promotion. A render-time value is accepted only as a
 *     PROVISIONAL seed and is outranked by the first server word.
 *
 *  2. A client-side zero NEVER navigates. Clock skew, a laptop resumed from
 *     sleep, or a stale attribute must not evict a paying-attention visitor.
 *     Only the SERVER ends a session, and it says so with 404/401/403 on
 *     /api/visitor/heartbeat/ (apps/infra/public_app/views/status/visitor.py:
 *     319-357; the 404 body also carries `"status": "expired"`). When the
 *     countdown reaches zero it renders "EXPIRED" and ASKS the server
 *     (`requestVisitorLeaseVerification`) instead of acting on its own belief.
 *
 * DO NOT "simplify" this by deleting PROBATION_SECONDS server-side. It is
 * deliberate anti-crawler defence added after the 2026-07-14 slot-squatting
 * incident, where a JS-less crawler held all 16 slots for an hour each and
 * every human got read-only. The bug was never that probation exists — it was
 * that the CLIENT treated the probation stamp as the session deadline.
 *
 * SINGLETON ACROSS BUNDLES. `shared/components/header` and
 * `shared/utils/visitor-heartbeat` are two separate Vite entries
 * (templates/global_base_partials/global_body_scripts.html:37,49). The store
 * is parked on `window` under a well-known key so the countdown and the
 * heartbeat share ONE lease no matter how Rollup chunks them.
 */

import { NAV_URLS } from "./api-urls";

/** Where the current deadline came from. `"render"` is PROVISIONAL. */
export type VisitorLeaseSource = "none" | "render" | "heartbeat";

export interface VisitorLeaseState {
  /** Best-known session deadline, or null when nothing is known yet. */
  expiresAt: Date | null;
  /** Provenance of `expiresAt`. */
  source: VisitorLeaseSource;
  /** True ONLY once the server has said the session is over. */
  serverExpired: boolean;
}

type VisitorLeaseListener = (state: VisitorLeaseState) => void;

/** A verifier asks the server whether the session is really over. */
type VisitorLeaseVerifier = () => unknown;

interface VisitorLeaseStore {
  expiresAt: Date | null;
  source: VisitorLeaseSource;
  serverExpired: boolean;
  listeners: Set<VisitorLeaseListener>;
  verifier: VisitorLeaseVerifier | null;
  verifyInFlight: boolean;
  lastVerifyAt: number;
}

const GLOBAL_KEY = "__scitexVisitorSessionLease";

/**
 * Do not re-ask the server more than once per this window. The countdown
 * ticks every second; without this, a stuck-at-zero countdown would beat the
 * heartbeat endpoint 60x a minute.
 */
const VERIFY_MIN_INTERVAL_MS = 15000;

/**
 * Pages where evicting the visitor is either a loop (/visitor-expired/ sends
 * them straight back) or actively hostile (they are in the middle of signing
 * up, which is the whole point of the funnel).
 */
const NO_EVICTION_PATH_PREFIXES: readonly string[] = [
  NAV_URLS.visitorExpired,
  "/visitor-restart/",
  "/visitor-pool-full/",
  "/auth/",
];

function store(): VisitorLeaseStore {
  const holder = window as unknown as Record<string, VisitorLeaseStore>;
  let existing = holder[GLOBAL_KEY];
  if (!existing) {
    existing = {
      expiresAt: null,
      source: "none",
      serverExpired: false,
      listeners: new Set<VisitorLeaseListener>(),
      verifier: null,
      verifyInFlight: false,
      lastVerifyAt: 0,
    };
    holder[GLOBAL_KEY] = existing;
  }
  return existing;
}

/** Immutable snapshot of the current lease. */
export function getVisitorLease(): VisitorLeaseState {
  const s = store();
  return {
    expiresAt: s.expiresAt ? new Date(s.expiresAt.getTime()) : null,
    source: s.source,
    serverExpired: s.serverExpired,
  };
}

function emit(): void {
  const snapshot = getVisitorLease();
  // Copy first: a listener may unsubscribe itself while we iterate.
  Array.from(store().listeners).forEach((listener) => {
    try {
      listener(snapshot);
    } catch (error) {
      console.error("[visitor-lease] listener failed:", error);
    }
  });
}

/** Subscribe to lease changes. Returns an unsubscribe function. */
export function subscribeVisitorLease(
  listener: VisitorLeaseListener,
): () => void {
  const s = store();
  s.listeners.add(listener);
  return () => {
    s.listeners.delete(listener);
  };
}

function parseIso(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const parsed = new Date(iso);
  return isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Seed the lease from a render-time `data-expires-at` attribute.
 *
 * PROVISIONAL ONLY. Once a heartbeat has spoken, a render-time value is
 * ignored — it is by construction the probation stamp of whichever page load
 * produced the HTML, and re-applying it would re-introduce the bug on every
 * subsequent navigation.
 *
 * @returns true when the seed was accepted.
 */
export function seedVisitorLeaseFromRender(
  iso: string | null | undefined,
): boolean {
  const parsed = parseIso(iso);
  if (!parsed) return false;
  const s = store();
  if (s.source === "heartbeat") return false;
  s.expiresAt = parsed;
  s.source = "render";
  emit();
  return true;
}

/**
 * Record the authoritative deadline from a heartbeat response.
 *
 * This is the half of the fix that makes the countdown track the real lease:
 * the server extends `expires_at` on every beat, and the client now reads it.
 *
 * @returns true when a usable timestamp was recorded.
 */
export function recordVisitorLeaseFromHeartbeat(
  iso: string | null | undefined,
): boolean {
  const parsed = parseIso(iso);
  if (!parsed) return false;
  const s = store();
  const changed =
    s.source !== "heartbeat" ||
    s.expiresAt === null ||
    s.expiresAt.getTime() !== parsed.getTime();
  s.expiresAt = parsed;
  s.source = "heartbeat";
  if (changed) emit();
  return true;
}

/**
 * The SERVER says this session is over — the only thing that may evict.
 *
 * Listeners are notified BEFORE navigating so the countdown can paint
 * "EXPIRED" on the way out. Terminal: once set it is never cleared, and
 * repeat calls do not navigate twice.
 */
export function recordVisitorSessionExpired(): void {
  const s = store();
  if (s.serverExpired) return;
  s.serverExpired = true;
  emit();
  if (canEvictFromPath()) {
    // replace(), not href: the expired page must not be a back-button trap.
    window.location.replace(NAV_URLS.visitorExpired);
  }
}

/**
 * Register the component that can ask the server about the session. The
 * heartbeat owns the endpoint, so it registers itself.
 */
export function registerVisitorLeaseVerifier(
  verifier: VisitorLeaseVerifier,
): void {
  store().verifier = verifier;
}

/**
 * Ask the server whether the session is really over.
 *
 * Called when the countdown believes it has hit zero. Throttled and
 * de-duplicated: a stuck countdown must not turn into a request flood.
 */
export function requestVisitorLeaseVerification(): void {
  const s = store();
  if (s.serverExpired || !s.verifier || s.verifyInFlight) return;
  const now = Date.now();
  if (s.lastVerifyAt && now - s.lastVerifyAt < VERIFY_MIN_INTERVAL_MS) return;

  s.verifyInFlight = true;
  s.lastVerifyAt = now;
  let result: unknown;
  try {
    result = s.verifier();
  } catch (error) {
    s.verifyInFlight = false;
    console.warn("[visitor-lease] verification failed:", error);
    return;
  }
  Promise.resolve(result)
    .catch((error) => {
      console.warn("[visitor-lease] verification failed:", error);
    })
    .then(() => {
      s.verifyInFlight = false;
    });
}

/** Whether an eviction from `pathname` is safe (i.e. not a loop). */
export function canEvictFromPath(
  pathname: string = window.location.pathname,
): boolean {
  return !NO_EVICTION_PATH_PREFIXES.some((prefix) =>
    pathname.startsWith(prefix),
  );
}

/** Test seam: drop the shared store so each test starts from nothing. */
export function resetVisitorLeaseStore(): void {
  const holder = window as unknown as Record<string, unknown>;
  delete holder[GLOBAL_KEY];
}
