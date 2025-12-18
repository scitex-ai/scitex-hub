/**
 * Interaction Handlers Module
 *
 * Handles:
 * - Mouse events (click, drag, hover)
 * - Keyboard shortcuts
 * - Theme switching
 * - File tree integration
 */

import type { VisEditor } from "../VisEditor.ts";
import { setupThemeToggle, applySavedThemes } from "./theme.ts";
import { setupFilesTree } from "./files-tree.ts";
import { setupShortcutsHelp } from "./shortcuts.ts";
import { setupHitRegionToggle } from "./hit-regions.ts";

export interface InteractionHandlers {
  setupThemeToggle(): void;
  setupFilesTree(projectOwner: string, projectSlug: string): Promise<void>;
  setupShortcutsHelp(): void;
  setupHitRegionToggle(): void;
}

/**
 * Setup interaction handlers
 */
export function setupInteractionHandlers(
  editor: VisEditor,
): InteractionHandlers {
  // Apply themes on initialization
  applySavedThemes(editor);

  return {
    setupThemeToggle: () => setupThemeToggle(editor),
    setupFilesTree: (projectOwner: string, projectSlug: string) =>
      setupFilesTree(editor, projectOwner, projectSlug),
    setupShortcutsHelp,
    setupHitRegionToggle: () => setupHitRegionToggle(editor),
  };
}

// Re-export types for backward compatibility
export type { VisEditor };
