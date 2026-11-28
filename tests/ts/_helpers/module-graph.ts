/**
 * Helpers for tests that evaluate a side-effectful browser entrypoint with
 * `vi.resetModules()` + `await import()`.
 *
 * Two problems come with that pattern:
 *
 * 1. The first `await import()` in a file transforms the whole module graph
 *    on the Vite server. All workers share that server, so on a loaded CI
 *    host the request waits behind every other worker's transforms. When the
 *    import happens inside a test body, that wait counts against the test's
 *    5 s budget and the test times out without having run any of its
 *    assertions. `warmModuleGraph()` does the first transform at collection
 *    time (top-level await in the test file), which no test timeout covers.
 *    Later evaluations reuse the transformed code and take milliseconds.
 *
 * 2. Each evaluation registers `document` / `window` listeners that outlive
 *    the test, because jsdom keeps one document per file. Evaluations then
 *    pile up and a later test sees handlers from earlier ones.
 *    `recordGlobalListeners()` records what was added so it can be removed.
 */
import { vi } from "vitest";

type Registration = Parameters<EventTarget["addEventListener"]>;

/**
 * Record every listener added to `document` and `window` from now on.
 * The returned function removes those listeners and stops recording.
 */
export function recordGlobalListeners(): () => void {
  const recorded: Array<[EventTarget, Registration]> = [];
  // Under vitest's jsdom environment `window` is the global object and
  // `addEventListener` may be an own property of it, so keep whatever
  // descriptor was there and put it back exactly.
  const restores = ([document, window] as EventTarget[]).map((target) => {
    const own = Object.getOwnPropertyDescriptor(target, "addEventListener");
    const original = target.addEventListener;
    Object.defineProperty(target, "addEventListener", {
      configurable: true,
      writable: true,
      value: (...args: Registration) => {
        recorded.push([target, args]);
        return original.apply(target, args);
      },
    });
    return () => {
      if (own) Object.defineProperty(target, "addEventListener", own);
      else delete (target as { addEventListener?: unknown }).addEventListener;
    };
  });
  return () => {
    for (const restore of restores) restore();
    for (const [target, [type, listener, options]] of recorded.splice(0)) {
      target.removeEventListener(type, listener, options);
    }
  };
}

/**
 * Transform and evaluate a module graph once, then undo its global
 * listeners and clear the module registry so each test still gets a fresh
 * evaluation. Call it with top-level `await` in the test file, before any
 * `describe`. Pass a loader closure (`() => import("...")`) so the test
 * file resolves its own specifier and aliases.
 */
export async function warmModuleGraph(
  load: () => Promise<unknown>,
): Promise<void> {
  const release = recordGlobalListeners();
  try {
    await load();
  } finally {
    release();
    vi.resetModules();
  }
}
