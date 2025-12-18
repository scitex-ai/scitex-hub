/**
 * Filesystem sync operations for canvas tabs
 * Handles syncing tabs with figz files on disk
 */

import type { CanvasTab } from "./CanvasTabTypes";

/**
 * Find a tab by figure path
 */
export function findTabByFigurePath(
  tabs: CanvasTab[],
  figurePath: string,
): CanvasTab | undefined {
  const normalizePath = (p: string) => p.replace(/\.figz$/, "").toLowerCase();
  const normalizedInput = normalizePath(figurePath);

  return tabs.find((tab) => {
    if (!tab.figurePath) return false;
    const normalizedTab = normalizePath(tab.figurePath);
    return (
      normalizedTab === normalizedInput ||
      normalizedTab.endsWith(normalizedInput) ||
      normalizedInput.endsWith(normalizedTab)
    );
  });
}

/**
 * Extract figure name from path
 * e.g., "/path/to/Figure1.figz" -> "Figure1"
 */
export function extractFigureNameFromPath(figurePath: string): string {
  const parts = figurePath.split("/");
  let filename = parts[parts.length - 1];
  return filename.replace(/\.figz$/, "");
}

/**
 * Sync tabs with filesystem - returns tabs to add and tabs to remove
 *
 * @param currentTabs Current tabs array
 * @param validPaths Array of valid figz paths from the file tree
 * @returns Object with tabsToAdd (paths) and tabsToRemove (tab ids)
 */
export function calculateTabSync(
  currentTabs: CanvasTab[],
  validPaths: string[],
): {
  pathsToAdd: string[];
  tabIdsToRemove: string[];
} {
  const validPathSet = new Set(validPaths.map((p) => p.toLowerCase()));

  // Find paths that don't have matching tabs
  const pathsToAdd: string[] = [];
  for (const figzPath of validPaths) {
    const existingTab = findTabByFigurePath(currentTabs, figzPath);
    if (!existingTab) {
      pathsToAdd.push(figzPath);
    }
  }

  // Find tabs that don't have matching paths (orphans)
  const tabIdsToRemove: string[] = [];
  for (const tab of currentTabs) {
    // Always keep the default tab
    if (tab.id === "default") continue;

    // Tabs without figurePath are orphans (unsaved) - remove them
    if (!tab.figurePath) {
      tabIdsToRemove.push(tab.id);
      console.log(
        `[CanvasTabSync] Marking orphan tab (unsaved): ${tab.figureName}`,
      );
      continue;
    }

    // Check if the figurePath exists in the tree
    const tabPath = tab.figurePath.toLowerCase();
    const exists =
      validPathSet.has(tabPath) ||
      Array.from(validPathSet).some(
        (vp) => tabPath.endsWith(vp) || vp.endsWith(tabPath),
      );

    if (!exists) {
      tabIdsToRemove.push(tab.id);
      console.log(
        `[CanvasTabSync] Marking stale tab: ${tab.figureName} (${tab.figurePath})`,
      );
    }
  }

  return { pathsToAdd, tabIdsToRemove };
}

/**
 * Generate a unique figure name based on existing tabs
 */
export function generateUniqueFigureName(existingNames: string[]): string {
  const lowerNames = existingNames.map((n) => n.toLowerCase());
  let counter = 1;
  while (
    lowerNames.includes(`figure${counter}`) ||
    lowerNames.includes(`figure ${counter}`)
  ) {
    counter++;
  }
  return `Figure${counter}`;
}

/**
 * Sanitize figure name for filesystem compatibility
 */
export function sanitizeFigureName(name: string): string {
  return name
    .replace(/\s+/g, "") // Remove all spaces
    .replace(/[<>:"/\\|?*]/g, "") // Remove invalid filename chars
    .trim();
}
