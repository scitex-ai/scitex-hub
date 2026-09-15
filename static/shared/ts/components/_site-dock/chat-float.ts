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
export const PHONE_MAX = 640;
const GAP = 8;
const MARGIN = 8;
const DESKTOP_W = 380;
const DESKTOP_H = 520;
const PHONE_H_RATIO = 0.5;
const PHONE_H_MAX = 520;

export function embedUrl(path: string, title: string): string {
  const qs = new URLSearchParams({
    embed: "1",
    ctx_path: path.slice(0, 200),
    ctx_title: title.slice(0, 120),
  });
  return `${CHAT_URL}?${qs.toString()}`;
}

/** The panel sits just above the dock (below it when the dock is near the top). */
export function panelRect(
  dock: Rect,
  vp: { width: number; height: number },
): Rect {
  const phone = vp.width <= PHONE_MAX;
  const width = phone ? dock.width : Math.min(DESKTOP_W, vp.width - 2 * MARGIN);
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
