/**
 * Workspace Files Tree - Read-only mode
 *
 * A viewer who cannot write to a project (someone else's public project, an
 * anonymous visitor) must not be OFFERED new file / upload / rename / delete /
 * move / paste / git writes. The server refuses those writes anyway
 * (Project.can_edit); this keeps the tree from proposing actions that can only
 * fail. Enabled with TreeConfig.readOnly, which auto-init reads from the
 * mount's data-read-only="true" attribute.
 */

import type { ContextMenuItem } from "./_handlers/ContextMenuHandler";

/** Context-menu actions that only read. Everything else is a write. */
export const READ_ONLY_ACTIONS: ReadonlySet<string> = new Set([
  "copy",
  "download",
  "filter",
  "refresh",
  "git-history",
  "git-diff",
]);

export function isWriteAction(action: string): boolean {
  return !READ_ONLY_ACTIONS.has(action);
}

/** Drop write items (and submenus left empty) plus dangling separators. */
export function filterReadOnlyMenu(
  items: ContextMenuItem[],
): ContextMenuItem[] {
  const kept: ContextMenuItem[] = [];
  for (const item of items) {
    if (item.separator) {
      if (kept.length && !kept[kept.length - 1].separator) kept.push(item);
      continue;
    }
    if (item.children) {
      const children = filterReadOnlyMenu(item.children);
      if (children.length) kept.push({ ...item, children });
      continue;
    }
    if (item.action && READ_ONLY_ACTIONS.has(item.action)) kept.push(item);
  }
  while (kept.length && kept[kept.length - 1].separator) kept.pop();
  return kept;
}

/** Keyboard shortcuts that would change the project (cut, paste, delete…). */
export function isWriteShortcut(e: KeyboardEvent): boolean {
  const mod = e.ctrlKey || e.metaKey;
  const key = e.key.toLowerCase();
  if (mod && ["x", "v", "z", "y", "n"].includes(key)) return true;
  if (!mod && ["delete", "backspace", "f2"].includes(key)) return true;
  return !mod && !e.altKey && (e.key === "+" || e.key === "=");
}
