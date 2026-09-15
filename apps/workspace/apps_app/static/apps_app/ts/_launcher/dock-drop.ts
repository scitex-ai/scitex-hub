/**
 * Dock drop rules — pure decisions for dragging apps between the grid and the
 * dock. Every app is in exactly one of the two, like an iPhone home screen.
 * dock-editor.ts measures the DOM and applies what these functions decide.
 */

export interface Point {
  x: number;
  y: number;
}

export interface Box {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export type DropZone = "dock" | "grid";

export type DockRefusal = "full" | "fixed";

export interface DockChange {
  accepted: boolean;
  dock: string[];
  refusal?: DockRefusal;
}

// A finger rarely lands exactly on the dock edge, so the dock catches drops slightly outside it.
export const DOCK_DROP_SLOP_PX = 12;

// Smallest slot an app button may shrink to before the dock counts as full.
export const MIN_DOCK_SLOT_PX = 40;

export function dropZoneFor(
  point: Point,
  dock: Box | null,
  slop = DOCK_DROP_SLOP_PX,
): DropZone {
  if (!dock) return "grid";
  const insideX = point.x >= dock.left - slop && point.x <= dock.right + slop;
  const insideY = point.y >= dock.top - slop && point.y <= dock.bottom + slop;
  return insideX && insideY ? "dock" : "grid";
}

/** Slot index for a pointer, given the centres of the dock buttons it would land among. */
export function dockInsertIndex(
  pointerX: number,
  slotCenters: number[],
): number {
  return slotCenters.filter((center) => center < pointerX).length;
}

/** How many apps fit: the server's limit, or fewer when the dock is too narrow. */
export function dockCapacity(
  appsWidth: number,
  serverCapacity: number,
  minSlot = MIN_DOCK_SLOT_PX,
): number {
  // Before layout (or in jsdom) there is no width to measure.
  if (!(appsWidth > 0)) return serverCapacity;
  return Math.max(1, Math.min(serverCapacity, Math.floor(appsWidth / minSlot)));
}

/**
 * Put ``app`` into the dock at ``index`` (counted among the OTHER docked apps).
 * An app already in the dock is only moved, so it never needs a free slot.
 */
export function dropIntoDock(
  dock: string[],
  app: string,
  index: number,
  capacity: number,
): DockChange {
  const others = dock.filter((name) => name !== app);
  const alreadyDocked = others.length !== dock.length;
  if (!alreadyDocked && dock.length >= capacity) {
    return { accepted: false, dock, refusal: "full" };
  }
  const at = Math.min(Math.max(0, index), others.length);
  return {
    accepted: true,
    dock: [...others.slice(0, at), app, ...others.slice(at)],
  };
}

/** Take ``app`` out of the dock, unless it is one that must stay there (Home). */
export function dropOutOfDock(
  dock: string[],
  app: string,
  fixedApps: readonly string[],
): DockChange {
  if (fixedApps.includes(app)) {
    return { accepted: false, dock, refusal: "fixed" };
  }
  return { accepted: true, dock: dock.filter((name) => name !== app) };
}
