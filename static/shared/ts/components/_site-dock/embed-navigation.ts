/**
 * Typed, same-origin navigation bridge for the floating Chat iframe.
 *
 * The child may request one narrowly allow-listed parent navigation. The parent
 * still authenticates the MessageEvent's origin and source before acting.
 */

export const EMBED_PARENT_NAVIGATION = "stx-chat-parent-navigate" as const;
export const AI_PROVIDER_SETTINGS_PATH = "/accounts/settings/ai-providers/";

export interface EmbedParentNavigationMessage {
  type: typeof EMBED_PARENT_NAVIGATION;
  href: string;
}

export interface EmbeddedNavigationWindow {
  location: { origin: string };
  parent: ParentMessenger;
}

interface ParentMessenger {
  postMessage(message: EmbedParentNavigationMessage, targetOrigin: string): void;
}

/** Return the allow-listed same-origin target as a path, never an absolute URL. */
export function parentNavigationPath(
  href: unknown,
  origin: string,
): string | null {
  if (typeof href !== "string") return null;
  try {
    const currentOrigin = new URL(origin).origin;
    const target = new URL(href, currentOrigin);
    if (target.origin !== currentOrigin) return null;
    if (target.protocol !== "http:" && target.protocol !== "https:") return null;
    if (target.username || target.password) return null;
    if (target.pathname !== AI_PROVIDER_SETTINGS_PATH) return null;
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return null;
  }
}

function isNavigationMessage(
  value: unknown,
): value is EmbedParentNavigationMessage {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const candidate = value as Partial<EmbedParentNavigationMessage>;
  return (
    candidate.type === EMBED_PARENT_NAVIGATION &&
    typeof candidate.href === "string"
  );
}

/** Authenticate a parent-side message and return its safe navigation path. */
export function trustedParentNavigationPath(
  event: MessageEvent,
  trustedSource: WindowProxy | null,
  origin: string,
): string | null {
  if (!trustedSource || event.source !== trustedSource) return null;
  if (event.origin !== origin || !isNavigationMessage(event.data)) return null;
  return parentNavigationPath(event.data.href, origin);
}

/** Post a validated navigation command when running inside the floating iframe. */
export function postParentNavigation(
  href: unknown,
  browserWindow: EmbeddedNavigationWindow = window,
): boolean {
  const target = parentNavigationPath(href, browserWindow.location.origin);
  if (
    !target ||
    browserWindow.parent === (browserWindow as unknown as ParentMessenger)
  )
    return false;
  browserWindow.parent.postMessage(
    { type: EMBED_PARENT_NAVIGATION, href: target },
    browserWindow.location.origin,
  );
  return true;
}
