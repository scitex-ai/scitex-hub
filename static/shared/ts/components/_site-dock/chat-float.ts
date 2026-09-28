/**
 * Floating dock chat — pure geometry and URL helpers (DOM wiring in site-dock.ts).
 */

export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export const CHAT_URL = "/chat/";
export const EMBED_NAVIGATION_MESSAGE = "stx-embed-navigate";
export const PHONE_MAX = 640;
const GAP = 8;
const MARGIN = 8;
const DESKTOP_W = 380;
const DESKTOP_H = 520;
const PHONE_H_RATIO = 0.5;
const PHONE_H_MAX = 520;

export type EmbedTheme = "light" | "dark";

/** postMessage type the parent sends when its theme changes (theme-switcher.ts listens). */
export const EMBED_THEME_MESSAGE = "stx-embed-theme";

/** Validate an iframe navigation request and return a same-origin path. */
export function parentNavigationUrl(
  href: unknown,
  origin: string,
): string | null {
  if (typeof href !== "string") return null;
  try {
    const target = new URL(href, origin);
    if (target.origin !== origin) return null;
    if (target.protocol !== "http:" && target.protocol !== "https:") return null;
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return null;
  }
}

/** The page's effective theme: its data-theme, else the OS preference. */
export function effectiveTheme(
  dataTheme: string | null,
  prefersDark: boolean,
): EmbedTheme {
  if (dataTheme === "light" || dataTheme === "dark") return dataTheme;
  return prefersDark ? "dark" : "light";
}

export function embedUrl(
  path: string,
  title: string,
  theme?: EmbedTheme,
): string {
  const qs = new URLSearchParams({
    embed: "1",
    ctx_path: path.slice(0, 200),
    ctx_title: title.slice(0, 120),
  });
  if (theme) qs.set("theme", theme);
  return `${CHAT_URL}?${qs.toString()}`;
}

const MAX_W = 1100;
const MAX_H = 900;

export function toggleMaximized(maximized: boolean): boolean {
  return !maximized;
}

/** Maximized: nearly the whole viewport on the dock's free side, centred on desktop. */
export function maximizedRect(
  dock: Rect,
  vp: { width: number; height: number },
): Rect {
  const above = dock.top - GAP - MARGIN;
  const below = vp.height - (dock.top + dock.height) - GAP - MARGIN;
  const placeAbove = above >= below;
  const room = Math.max(160, placeAbove ? above : below);
  const areaTop = placeAbove ? MARGIN : dock.top + dock.height + GAP;
  const phone = vp.width <= PHONE_MAX;
  const width = phone
    ? vp.width - 2 * MARGIN
    : Math.min(MAX_W, vp.width - 2 * MARGIN);
  const height = phone ? room : Math.min(MAX_H, room);
  return {
    left: Math.round((vp.width - width) / 2),
    top: Math.round(areaTop + (room - height) / 2),
    width,
    height,
  };
}

/** The panel sits just above the dock (below it when the dock is near the top). */
export function panelRect(
  dock: Rect,
  vp: { width: number; height: number },
): Rect {
  const phone = vp.width <= PHONE_MAX;
  // A minimized dock is a small pill; the panel keeps a usable phone width.
  const phoneW = dock.width < 240 ? vp.width - 2 * MARGIN : dock.width;
  const width = phone ? phoneW : Math.min(DESKTOP_W, vp.width - 2 * MARGIN);
  const wanted = phone
    ? Math.min(vp.height * PHONE_H_RATIO, PHONE_H_MAX)
    : DESKTOP_H;
  const above = dock.top - GAP - MARGIN;
  const below = vp.height - (dock.top + dock.height) - GAP - MARGIN;
  const placeAbove = above >= Math.min(wanted, 240) || above >= below;
  const height = Math.max(160, Math.min(wanted, placeAbove ? above : below));
  const top = placeAbove
    ? dock.top - GAP - height
    : dock.top + dock.height + GAP;
  const centred = dock.left + dock.width / 2 - width / 2;
  const left = Math.min(
    Math.max(MARGIN, centred),
    Math.max(MARGIN, vp.width - width - MARGIN),
  );
  return { left, top, width, height };
}
