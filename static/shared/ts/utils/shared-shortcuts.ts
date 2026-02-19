/**
 * Shared Shortcuts - Centralized global keyboard shortcuts
 *
 * IMPORTANT: These shortcuts are reserved system-wide and MUST NOT be overridden
 * by any app-specific shortcuts. If a conflict is detected, an error will be logged.
 *
 * Reserved Shortcuts:
 * - Alt+A: Toggle AI Assistant
 * - Alt+Z: Toggle Zen Mode
 * - Alt+F: Go to Files Mode
 * - Alt+S: Go to Scholar Mode
 * - Alt+C: Go to Code Mode
 * - Alt+T: Go to Tools
 * - Alt+V: Go to Vis Mode
 * - Alt+W: Go to Writer Mode
 * - Alt+/: Show Keyboard Shortcuts Help
 * - F11: Cycle Zen/Fullscreen modes
 * - Esc: Exit Zen/Fullscreen mode (when in zen mode)
 */

export interface SharedShortcut {
  key: string;
  altKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
  description: string;
  action: string;
}

/**
 * Reserved shared shortcuts - these MUST NOT be overridden
 */
export const SHARED_SHORTCUTS: SharedShortcut[] = [
  {
    key: "a",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Toggle AI Assistant",
    action: "toggle-ai",
  },
  {
    key: "t",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Go to Tools",
    action: "navigate-tools",
  },
  {
    key: "z",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Toggle Zen Mode",
    action: "zen-mode",
  },
  {
    key: "f",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Go to Files",
    action: "navigate-files",
  },
  {
    key: "s",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Go to Scholar",
    action: "navigate-scholar",
  },
  {
    key: "c",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Go to Code",
    action: "navigate-code",
  },
  {
    key: "v",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Go to Vis",
    action: "navigate-vis",
  },
  {
    key: "w",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Go to Writer",
    action: "navigate-writer",
  },
  {
    key: "/",
    altKey: true,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Show Keyboard Shortcuts",
    action: "show-shortcuts",
  },
  {
    key: "F11",
    altKey: false,
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    description: "Cycle Zen/Fullscreen modes",
    action: "zen-cycle",
  },
];

/**
 * Generate a unique key identifier for a shortcut
 */
function getShortcutKey(shortcut: {
  key: string;
  altKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
}): string {
  const parts: string[] = [];
  if (shortcut.ctrlKey) parts.push("Ctrl");
  if (shortcut.altKey) parts.push("Alt");
  if (shortcut.shiftKey) parts.push("Shift");
  if (shortcut.metaKey) parts.push("Meta");
  parts.push(shortcut.key.toLowerCase());
  return parts.join("+");
}

/**
 * Check if a keyboard event matches a shared shortcut
 */
export function matchesSharedShortcut(e: KeyboardEvent): SharedShortcut | null {
  const key = e.key.toLowerCase();

  for (const shortcut of SHARED_SHORTCUTS) {
    if (
      key === shortcut.key.toLowerCase() &&
      e.altKey === shortcut.altKey &&
      e.ctrlKey === shortcut.ctrlKey &&
      e.shiftKey === shortcut.shiftKey &&
      e.metaKey === shortcut.metaKey
    ) {
      return shortcut;
    }
  }
  return null;
}

/**
 * Check if a proposed shortcut conflicts with shared shortcuts
 * @returns The conflicting shortcut if found, null otherwise
 */
export function checkShortcutConflict(
  key: string,
  altKey: boolean = false,
  ctrlKey: boolean = false,
  shiftKey: boolean = false,
  metaKey: boolean = false,
): SharedShortcut | null {
  const proposedKey = getShortcutKey({
    key,
    altKey,
    ctrlKey,
    shiftKey,
    metaKey,
  });

  for (const shortcut of SHARED_SHORTCUTS) {
    const reservedKey = getShortcutKey(shortcut);
    if (proposedKey === reservedKey) {
      return shortcut;
    }
  }
  return null;
}

/**
 * Register an app-specific shortcut with conflict detection
 * Logs an error if the shortcut conflicts with a shared shortcut
 *
 * @param key - The key to register
 * @param modifiers - Modifier keys (alt, ctrl, shift, meta)
 * @param description - Description of the shortcut
 * @param handler - The handler function
 * @returns true if registered successfully, false if conflict detected
 */
export function registerAppShortcut(
  key: string,
  modifiers: {
    altKey?: boolean;
    ctrlKey?: boolean;
    shiftKey?: boolean;
    metaKey?: boolean;
  },
  description: string,
  handler: (e: KeyboardEvent) => void,
): boolean {
  const conflict = checkShortcutConflict(
    key,
    modifiers.altKey || false,
    modifiers.ctrlKey || false,
    modifiers.shiftKey || false,
    modifiers.metaKey || false,
  );

  if (conflict) {
    console.error(
      `[SharedShortcuts] CONFLICT: Cannot register "${description}" ` +
        `(${getShortcutKey({ key, ...modifiers, altKey: modifiers.altKey || false, ctrlKey: modifiers.ctrlKey || false, shiftKey: modifiers.shiftKey || false, metaKey: modifiers.metaKey || false })}) - ` +
        `Reserved for "${conflict.description}" (${conflict.action})`,
    );
    return false;
  }

  // No conflict, safe to register
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    if (
      e.key.toLowerCase() === key.toLowerCase() &&
      e.altKey === (modifiers.altKey || false) &&
      e.ctrlKey === (modifiers.ctrlKey || false) &&
      e.shiftKey === (modifiers.shiftKey || false) &&
      e.metaKey === (modifiers.metaKey || false)
    ) {
      handler(e);
    }
  });

  console.log(
    `[SharedShortcuts] Registered: ${description} (${getShortcutKey({ key, ...modifiers, altKey: modifiers.altKey || false, ctrlKey: modifiers.ctrlKey || false, shiftKey: modifiers.shiftKey || false, metaKey: modifiers.metaKey || false })})`,
  );
  return true;
}

/**
 * Get formatted list of all shared shortcuts for display
 */
export function getSharedShortcutsList(): string {
  return SHARED_SHORTCUTS.map((s) => {
    const keyCombo = getShortcutKey(s);
    return `${keyCombo}: ${s.description}`;
  }).join("\n");
}

/**
 * Get shared shortcuts as HTML for modal display
 */
export function getSharedShortcutsHTML(): string {
  let html = "<h3>Global Shortcuts (Always Active)</h3><ul>";
  for (const shortcut of SHARED_SHORTCUTS) {
    const keyCombo = getShortcutKey(shortcut);
    const displayKey = keyCombo
      .replace(/\+/g, " + ")
      .replace("alt", "Alt")
      .replace("ctrl", "Ctrl");
    html += `<li><kbd>${displayKey}</kbd> - ${shortcut.description}</li>`;
  }
  html += "</ul>";
  return html;
}

// Log shared shortcuts on module load
console.log("[SharedShortcuts] Reserved shortcuts:");
SHARED_SHORTCUTS.forEach((s) => {
  console.log(`  ${getShortcutKey(s)}: ${s.description}`);
});
