/**
 * Global Ctrl+P / Ctrl+N input history for all text inputs.
 *
 * Emacs-style navigation: Ctrl+P recalls the previous (older) entry,
 * Ctrl+N moves forward (newer). History is persisted per-input in localStorage.
 */

const STORAGE_PREFIX = "scitex:input-history:";
const MAX_ENTRIES = 50;

/** Per-input navigation state (not persisted — resets on page load). */
const cursors = new Map<string, number>();
const drafts = new Map<string, string>();

function getKey(el: HTMLElement): string {
  return (
    el.id ||
    (el as HTMLInputElement).name ||
    (el as HTMLElement).dataset.historyKey ||
    "anonymous"
  );
}

function load(key: string): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function save(key: string, entries: string[]): void {
  localStorage.setItem(
    STORAGE_PREFIX + key,
    JSON.stringify(entries.slice(-MAX_ENTRIES)),
  );
}

function push(key: string, value: string): void {
  if (!value.trim()) return;
  const entries = load(key);
  // Avoid consecutive duplicates
  if (entries[entries.length - 1] === value) return;
  entries.push(value);
  save(key, entries);
}

function prev(key: string, currentValue: string): string | null {
  const entries = load(key);
  if (entries.length === 0) return null;

  let cursor = cursors.get(key);
  if (cursor === undefined) {
    // First Ctrl+P — save what the user has typed as draft
    drafts.set(key, currentValue);
    cursor = entries.length;
  }

  if (cursor <= 0) return null; // already at oldest
  cursor -= 1;
  cursors.set(key, cursor);
  return entries[cursor] ?? null;
}

function next(key: string): string | null {
  const entries = load(key);
  let cursor = cursors.get(key);
  if (cursor === undefined) return null; // never navigated

  cursor += 1;
  if (cursor >= entries.length) {
    // Past newest — restore draft
    cursors.delete(key);
    return drafts.get(key) ?? "";
  }
  cursors.set(key, cursor);
  return entries[cursor] ?? null;
}

function resetCursor(key: string): void {
  cursors.delete(key);
  drafts.delete(key);
}

/** Check if element is a plain text input (not Monaco, xterm, contenteditable). */
function isPlainInput(
  el: Element | null,
): el is HTMLInputElement | HTMLTextAreaElement {
  if (!el) return false;
  if ((el as HTMLElement).isContentEditable) return false;
  if (el.closest(".monaco-editor, .xterm")) return false;

  if (el instanceof HTMLTextAreaElement) return true;
  if (el instanceof HTMLInputElement) {
    const type = el.type.toLowerCase();
    return (
      type === "" || type === "text" || type === "search" || type === "url"
    );
  }
  return false;
}

function handleKeydown(e: KeyboardEvent): void {
  const el = document.activeElement;
  if (!isPlainInput(el)) return;

  const key = getKey(el);

  if (e.key === "Enter" && !e.ctrlKey && !e.metaKey) {
    const value = el.value;
    push(key, value);
    resetCursor(key);
    return; // don't preventDefault — let the form/handler process Enter normally
  }

  if (!e.ctrlKey || e.altKey || e.shiftKey || e.metaKey) return;

  if (e.key === "p" || e.key === "P") {
    e.preventDefault();
    const value = prev(key, el.value);
    if (value !== null) {
      el.value = value;
      el.dispatchEvent(new Event("input", { bubbles: true }));
    }
  } else if (e.key === "n" || e.key === "N") {
    e.preventDefault();
    const value = next(key);
    if (value !== null) {
      el.value = value;
      el.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }
}

// Reset cursor when user types something new (not via history navigation)
function handleInput(e: Event): void {
  const el = e.target;
  if (!isPlainInput(el as Element)) return;
  // Only reset if we're not programmatically setting the value
  // (we dispatch synthetic "input" events from handleKeydown, but
  // those are not trusted — e.isTrusted distinguishes them)
  if (!(e as InputEvent).isTrusted) return;
  const key = getKey(el as HTMLElement);
  resetCursor(key);
}

function init(): void {
  document.addEventListener("keydown", handleKeydown, true);
  document.addEventListener("input", handleInput, true);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
