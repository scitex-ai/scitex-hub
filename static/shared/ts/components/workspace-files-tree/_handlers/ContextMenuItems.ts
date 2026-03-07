/**
 * ContextMenuItems - Menu item builders for file tree context menu
 *
 * Builds the item arrays for root, file, and submenu contexts.
 */

import type { ContextMenuItem, GitCounts } from "./ContextMenuHandler";

/** Helper: append " (N)" suffix when multiple items are selected */
function multi(label: string, count: number): string {
  return count > 1 ? `${label} (${count})` : label;
}

/** Git submenu items for a file/folder context */
export function buildGitFileSubmenu(n: number): ContextMenuItem[] {
  return [
    {
      label: multi("Stage", n),
      icon: "fa-plus",
      action: "git-stage",
      cssClass: "context-git-stage",
    },
    {
      label: multi("Unstage", n),
      icon: "fa-minus",
      action: "git-unstage",
      cssClass: "context-git-unstage",
    },
    {
      label: multi("Discard", n),
      icon: "fa-undo",
      action: "git-discard",
      cssClass: "context-git-discard",
    },
    { label: "", action: "", separator: true },
    {
      label: "History",
      icon: "fa-history",
      action: "git-history",
      cssClass: "context-git-history",
    },
    {
      label: "Diff",
      icon: "fa-code-compare",
      action: "git-diff",
      cssClass: "context-git-diff",
    },
  ];
}

/** Git submenu items for root (empty space) context */
export function buildGitRootSubmenu(gc: GitCounts): ContextMenuItem[] {
  return [
    {
      label: gc.unstaged ? `Stage All (${gc.unstaged})` : "Stage All",
      icon: "fa-plus",
      action: "git-stage-all",
      cssClass: "context-git-stage",
    },
    {
      label: gc.staged ? `Unstage All (${gc.staged})` : "Unstage All",
      icon: "fa-minus",
      action: "git-unstage-all",
      cssClass: "context-git-unstage",
    },
    { label: "", action: "", separator: true },
    {
      label: gc.staged ? `Commit (${gc.staged})...` : "Commit...",
      icon: "fa-check",
      action: "git-commit",
      cssClass: "context-git-stage",
    },
    {
      label: gc.staged ? `Commit & Push (${gc.staged})...` : "Commit & Push...",
      icon: "fa-upload",
      action: "git-commit-push",
      cssClass: "context-git-history",
    },
    { label: "", action: "", separator: true },
    {
      label: "Push",
      icon: "fa-cloud-arrow-up",
      action: "git-push",
      cssClass: "context-git-history",
    },
    {
      label: "Pull",
      icon: "fa-cloud-arrow-down",
      action: "git-pull",
      cssClass: "context-git-history",
    },
  ];
}

/** Build root context menu (right-click on empty space) */
export function buildRootMenuItems(
  hasClipboard: boolean,
  canUndo: boolean,
  canRedo: boolean,
  gc: GitCounts,
): ContextMenuItem[] {
  return [
    {
      label: "New File",
      icon: "fa-file",
      action: "new-file",
      cssClass: "context-new-file",
    },
    {
      label: "New Folder",
      icon: "fa-folder",
      action: "new-folder",
      cssClass: "context-new-folder",
    },
    { label: "", action: "", separator: true },
    {
      label: "Paste",
      icon: "fa-paste",
      action: "paste",
      shortcut: "Ctrl+V",
      disabled: !hasClipboard,
    },
    { label: "", action: "", separator: true },
    {
      label: "Undo",
      icon: "fa-undo",
      action: "undo",
      shortcut: "Ctrl+Z",
      disabled: !canUndo,
    },
    {
      label: "Redo",
      icon: "fa-redo",
      action: "redo",
      shortcut: "Ctrl+Y",
      disabled: !canRedo,
    },
    { label: "", action: "", separator: true },
    {
      label: "Git",
      icon: "fa-code-branch",
      action: "",
      cssClass: "context-git-submenu",
      children: buildGitRootSubmenu(gc),
    },
    { label: "", action: "", separator: true },
    {
      label: "Filter",
      icon: "fa-search",
      action: "filter",
      shortcut: "Ctrl+K",
    },
    { label: "Refresh", icon: "fa-refresh", action: "refresh" },
  ];
}

/** Runnable file extensions */
const RUNNABLE_EXTS = [".py", ".sh", ".js"];

/** Build file/folder context menu */
export function buildFileMenuItems(
  n: number,
  isDir: boolean,
  currentPath: string | null,
  hasClipboard: boolean,
  canUndo: boolean,
  canRedo: boolean,
): ContextMenuItem[] {
  const items: ContextMenuItem[] = [];

  // Run — only for executable file types (not directories, single selection)
  if (!isDir && n <= 1 && currentPath) {
    const ext = currentPath.substring(currentPath.lastIndexOf("."));
    if (RUNNABLE_EXTS.includes(ext)) {
      items.push({
        label: "Run",
        icon: "fa-play",
        action: "run-file",
        cssClass: "context-run-file",
      });
      items.push({ label: "", action: "", separator: true });
    }
  }

  // Clipboard
  items.push(
    {
      label: multi("Cut", n),
      icon: "fa-cut",
      action: "cut",
      shortcut: "Ctrl+X",
    },
    {
      label: multi("Copy", n),
      icon: "fa-copy",
      action: "copy",
      shortcut: "Ctrl+C",
    },
    {
      label: "Paste",
      icon: "fa-paste",
      action: "paste",
      shortcut: "Ctrl+V",
      disabled: !hasClipboard,
    },
  );
  items.push({ label: "", action: "", separator: true });

  // Rename / Delete
  if (n <= 1) {
    items.push({
      label: "Rename",
      icon: "fa-pen",
      action: "rename",
      shortcut: "F2",
      cssClass: "context-rename",
    });
  }
  items.push({
    label: multi("Delete", n),
    icon: "fa-trash",
    action: "delete",
    shortcut: "Del",
    cssClass: "context-delete",
  });
  items.push({ label: "", action: "", separator: true });

  // Download / Symlink
  items.push(
    { label: multi("Download", n), icon: "fa-download", action: "download" },
    {
      label: multi("Create Symlink", n),
      icon: "fa-link",
      action: "create-symlink",
    },
  );

  // Bundle operations for .figz and .pltz files
  if (
    n <= 1 &&
    currentPath &&
    (currentPath.endsWith(".figz") || currentPath.endsWith(".pltz"))
  ) {
    items.push({
      label: "Extract Bundle",
      icon: "fa-folder-open",
      action: "extract-bundle",
      cssClass: "context-extract-bundle",
    });
  }

  // ── SECTION DIVIDER ──
  items.push({
    label: "",
    action: "",
    separator: true,
    cssClass: "context-section-divider",
  });

  // New file/folder
  items.push(
    {
      label: "New File",
      icon: "fa-file",
      action: "new-file",
      cssClass: "context-new-file",
    },
    {
      label: "New Folder",
      icon: "fa-folder",
      action: "new-folder",
      cssClass: "context-new-folder",
    },
  );
  items.push({ label: "", action: "", separator: true });

  // Git submenu
  items.push({
    label: "Git",
    icon: "fa-code-branch",
    action: "",
    cssClass: "context-git-submenu",
    children: buildGitFileSubmenu(n),
  });

  // Tools
  items.push({
    label: "Clew",
    icon: "fa-fingerprint",
    action: "clew",
    cssClass: "context-clew",
  });
  items.push({ label: "", action: "", separator: true });

  // Utility
  items.push(
    {
      label: "Undo",
      icon: "fa-undo",
      action: "undo",
      shortcut: "Ctrl+Z",
      disabled: !canUndo,
    },
    {
      label: "Redo",
      icon: "fa-redo",
      action: "redo",
      shortcut: "Ctrl+Y",
      disabled: !canRedo,
    },
  );
  items.push({ label: "", action: "", separator: true });
  items.push({
    label: "Filter",
    icon: "fa-search",
    action: "filter",
    shortcut: "Ctrl+K",
  });

  return items;
}
