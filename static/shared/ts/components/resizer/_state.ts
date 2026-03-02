/**
 * LocalStorage persistence helpers for the Resizer system.
 * Handles saving/restoring panel sizes and collapse states.
 */

const LOG = "[Resizer]";

/** Generate a storage key from two panel selectors */
export function makeStorageKey(first: string, second: string): string {
  const clean = (s: string) => s.replace(/[^a-zA-Z0-9-]/g, "").toLowerCase();
  return `scitex-resizer-${clean(first)}-${clean(second)}`;
}

/** Save panel size (width or height) in pixels */
export function saveSize(key: string, size: number): void {
  try {
    localStorage.setItem(key, size.toString());
  } catch (e) {
    console.warn(`${LOG} Failed to save size for ${key}:`, e);
  }
}

/** Restore panel size from localStorage. Returns null if not found or invalid. */
export function restoreSize(key: string): number | null {
  try {
    const saved = localStorage.getItem(key);
    if (saved) {
      const size = parseInt(saved, 10);
      if (!isNaN(size) && size > 0) return size;
    }
  } catch (e) {
    console.warn(`${LOG} Failed to restore size for ${key}:`, e);
  }
  return null;
}

/** Save collapse state */
export function saveCollapsed(key: string, collapsed: boolean): void {
  try {
    localStorage.setItem(key + "-collapsed", collapsed.toString());
  } catch (e) {
    console.warn(`${LOG} Failed to save collapsed state:`, e);
  }
}

/** Restore collapse state. Returns null if no saved state. */
export function restoreCollapsed(key: string): boolean | null {
  try {
    const saved = localStorage.getItem(key + "-collapsed");
    if (saved === "true") return true;
    if (saved === "false") return false;
  } catch (e) {
    console.warn(`${LOG} Failed to restore collapsed state:`, e);
  }
  return null;
}

/**
 * Get a valid expand width from localStorage.
 * Returns null if saved width is too small, too large, or missing.
 */
export function getValidExpandSize(
  key: string,
  minSize: number,
  container: HTMLElement | null,
): number | null {
  const saved = restoreSize(key);
  if (!saved || saved <= minSize + 10) return null;
  if (container) {
    const maxS = container.offsetWidth * 0.8;
    if (saved > maxS && maxS > 100) return null;
  }
  return saved;
}
