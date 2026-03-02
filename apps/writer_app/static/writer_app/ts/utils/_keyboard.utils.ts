/**
 * Keyboard event utilities
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/keyboard.utils.ts loaded",
);
export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  callback: (event: KeyboardEvent) => void;
}

/**
 * Check if keyboard event matches a shortcut
 */
export function matchesShortcut(
  event: KeyboardEvent,
  key: string,
  options?: {
    ctrl?: boolean;
    shift?: boolean;
    alt?: boolean;
    meta?: boolean;
  },
): boolean {
  const keyMatch = event.key.toLowerCase() === key.toLowerCase();
  const ctrlMatch = (options?.ctrl ?? false) === event.ctrlKey;
  const shiftMatch = (options?.shift ?? false) === event.shiftKey;
  const altMatch = (options?.alt ?? false) === event.altKey;
  const metaMatch = (options?.meta ?? false) === event.metaKey;

  return keyMatch && ctrlMatch && shiftMatch && altMatch && metaMatch;
}

/**
 * Register keyboard shortcut
 */
export function registerShortcut(shortcut: KeyboardShortcut): () => void {
  const handler = (event: KeyboardEvent) => {
    if (
      matchesShortcut(event, shortcut.key, {
        ctrl: shortcut.ctrl,
        shift: shortcut.shift,
        alt: shortcut.alt,
        meta: shortcut.meta,
      })
    ) {
      event.preventDefault();
      shortcut.callback(event);
    }
  };

  document.addEventListener("keydown", handler);

  // Return unregister function
  return () => document.removeEventListener("keydown", handler);
}

/**
 * Get human-readable shortcut string
 */
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = [];

  if (shortcut.ctrl) parts.push("Ctrl");
  if (shortcut.alt) parts.push("Alt");
  if (shortcut.shift) parts.push("Shift");
  if (shortcut.meta) parts.push("Meta");

  parts.push(shortcut.key.toUpperCase());

  return parts.join("+");
}

/**
 * Check if event is from input element
 */
export function isInputElement(element: Element): boolean {
  const inputElements = ["INPUT", "TEXTAREA", "SELECT"];
  return (
    inputElements.includes(element.tagName) ||
    element.getAttribute("contenteditable") === "true"
  );
}
