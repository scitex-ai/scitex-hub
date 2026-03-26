/**
 * Sidebar keyboard shortcuts — Alt+key pane switching, "/" search.
 */

type PaneId = "chat" | "console" | "files" | "editor" | "module";

export function handleSidebarKeyDown(
  e: KeyboardEvent,
  switchPane: (pane: PaneId, updateHash: boolean) => void,
): void {
  // "/" shortcut to focus search (like GitHub/old SciTeX)
  if (
    e.key === "/" &&
    !e.altKey &&
    !e.ctrlKey &&
    !e.metaKey &&
    !(e.target instanceof HTMLInputElement) &&
    !(e.target instanceof HTMLTextAreaElement)
  ) {
    e.preventDefault();
    window.location.href = "/search/";
    return;
  }

  if (!e.altKey || e.ctrlKey || e.metaKey) return;

  const key = e.key.toLowerCase();
  let pane: PaneId | null = null;

  switch (key) {
    case "a":
      pane = "chat";
      break;
    case "t":
      pane = "console";
      break;
    case "e":
      pane = "editor";
      break;
    default:
      return;
  }

  if (pane) {
    e.preventDefault();
    switchPane(pane, true);
  }
}
