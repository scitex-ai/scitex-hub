/**
 * Workspace Files Tree - Filtering
 * Mode-specific filtering for different workspace modules
 *
 * Uses centralized configuration from FilteringCriteria.ts
 */

import type { TreeItem, FilterConfig, WorkspaceMode } from "./types.ts";
import { MODE_FILTERS } from "./types.ts";
import {
  ALLOW_EXTENSIONS,
  DENY_DIRECTORIES,
  ALLOW_DIRECTORIES,
  ALWAYS_VISIBLE_FILENAMES,
} from "./FilteringCriteria.ts";

export class TreeFilter {
  private config: FilterConfig;
  private showHidden = false;
  private moduleFilterEnabled = false;

  constructor(mode: WorkspaceMode, customConfig?: Partial<FilterConfig>) {
    // Use centralized FilteringCriteria configuration as default
    const centralExtensions = ALLOW_EXTENSIONS[mode];
    const defaultAllowedExtensions =
      centralExtensions === "all" ? [] : centralExtensions;
    const defaultHiddenPatterns = DENY_DIRECTORIES[mode] || [];

    // Fall back to old MODE_FILTERS for backward compatibility
    const legacyDefaults = MODE_FILTERS[mode] || MODE_FILTERS.all;

    this.config = {
      mode,
      allowedExtensions:
        customConfig?.allowedExtensions ?? defaultAllowedExtensions,
      disabledExtensions:
        customConfig?.disabledExtensions ??
        legacyDefaults.disabledExtensions ??
        [],
      hiddenPatterns: customConfig?.hiddenPatterns ?? defaultHiddenPatterns,
    };
  }

  /** Check if a file/folder should be hidden completely */
  isHidden(item: TreeItem): boolean {
    const { name, type } = item;

    // ============================================
    // FILTERING CRITERIA - MINIMAL HIDING
    // ============================================
    // With the new inactive/gray approach, we show almost everything.
    // Only truly system files that add noise are hidden.

    // 0. Hide dotfiles when showHidden is false (highest priority toggle)
    if (!this.showHidden && name.startsWith(".")) {
      return true;
    }

    // 1. ALWAYS VISIBLE FILES (bypasses filtering below, but not dotfile toggle above)
    //    Files like .gitkeep should always be shown when hidden files are visible
    if (type === "file" && ALWAYS_VISIBLE_FILENAMES.includes(name)) {
      return false;
    }

    // 2. Hide only system noise files (not directories)
    //    .DS_Store, Thumbs.db, etc. - these have no value to show
    const systemNoiseFiles = [".DS_Store", "Thumbs.db"];
    if (type === "file" && systemNoiseFiles.includes(name)) {
      return true;
    }

    // 3. ALWAYS hide extracted bundle directories (.figz.d, .pltz.d)
    //    Users work with ZIP files (.figz, .pltz) only
    if (
      type === "directory" &&
      (name.endsWith(".figz.d") || name.endsWith(".pltz.d"))
    ) {
      return true;
    }

    // 3. DIRECTORY BLACKLIST - NO LONGER HIDES, just marks as inactive
    //    Items in blacklist directories are now shown but grayed out
    //    (handled by isInactive() method instead)

    // 3. DIRECTORY WHITELIST - NO LONGER HIDES, just marks as inactive
    //    Items outside allowed directories are shown but grayed out
    //    (handled by isInactive() method instead)

    // Everything else is shown (may be inactive/grayed but visible)
    return false;
  }

  /** Check if a file/folder should be shown as inactive (grayed out) */
  isInactive(item: TreeItem): boolean {
    // Skip module-specific filtering when disabled
    if (!this.moduleFilterEnabled) {
      return false;
    }

    const { name, path, type } = item;

    // 1. Items in blacklisted directories are shown but inactive
    for (const pattern of this.config.hiddenPatterns) {
      // Support suffix patterns (e.g., '.figz.d' matches 'Figure1.figz.d')
      if (pattern.startsWith(".") && name.endsWith(pattern)) {
        return true;
      }
      if (
        name === pattern ||
        path.includes(`/${pattern}/`) ||
        path.includes(`/${pattern}`)
      ) {
        return true;
      }
    }

    // 2. Items outside allowed directories are shown but inactive
    if (!this.isWithinAllowedDirectories(path)) {
      return true;
    }

    // 3. Files with non-allowed extensions are shown but inactive
    if (type === "file" && !this.isAllowed(item)) {
      return true;
    }

    return false;
  }

  /**
   * Check if a path is within allowed directories
   * This implements the directory whitelist
   */
  private isWithinAllowedDirectories(path: string): boolean {
    const allowedDirs = ALLOW_DIRECTORIES[this.config.mode];

    // No restrictions = all directories allowed
    if (allowedDirs.length === 0) {
      return true;
    }

    // Normalize path for comparison
    const normalizedPath = path.replace(/^\.\//, "");

    // Check if path is within or equal to any allowed directory
    const isInAllowedDir = allowedDirs.some((allowedDir) => {
      const normalizedAllowedDir = allowedDir.replace(/^\.\//, "");
      return (
        normalizedPath.startsWith(normalizedAllowedDir) ||
        normalizedPath === normalizedAllowedDir
      );
    });

    if (isInAllowedDir) {
      return true;
    }

    // Check if path is a parent directory of any allowed directory
    // (e.g., 'scitex' is parent of 'scitex/vis', so it should be shown)
    const isParentOfAllowedDir = allowedDirs.some((allowedDir) => {
      const normalizedAllowedDir = allowedDir.replace(/^\.\//, "");
      return normalizedAllowedDir.startsWith(normalizedPath + "/");
    });

    return isParentOfAllowedDir;
  }

  /** Check if a file is allowed (can be selected/opened) */
  isAllowed(item: TreeItem): boolean {
    // Directories are always allowed for navigation
    if (item.type === "directory") {
      return true;
    }

    // Always show files in ALWAYS_VISIBLE_FILENAMES (e.g., .gitkeep)
    if (ALWAYS_VISIBLE_FILENAMES.includes(item.name)) {
      return true;
    }

    // ============================================
    // FILTERING CRITERIA (Systematic Order)
    // ============================================

    // 3. EXTENSION WHITELIST (allowed extensions)
    //    If extension whitelist is specified, only those extensions are allowed
    if (this.config.allowedExtensions.length === 0) {
      return true; // No whitelist = all extensions allowed
    }

    const ext = this.getExtension(item.name);
    return this.config.allowedExtensions.includes(ext);
  }

  /** Check if a file should be grayed out (visible but not selectable) */
  isDisabled(item: TreeItem): boolean {
    // Only apply extension-based disabling when module filter is active
    if (!this.moduleFilterEnabled) return false;
    if (item.type === "directory") return false;

    if (ALWAYS_VISIBLE_FILENAMES.includes(item.name)) return false;

    const ext = this.getExtension(item.name);

    // ============================================
    // FILTERING CRITERIA (Systematic Order)
    // ============================================

    // 4. EXTENSION BLACKLIST (disabled extensions)
    //    Explicitly disabled extensions are grayed out
    if (this.config.disabledExtensions.includes(ext)) {
      return true;
    }

    // 5. EXTENSION WHITELIST (for disabling)
    //    If allowedExtensions is specified, files NOT in the list are disabled
    if (
      this.config.allowedExtensions.length > 0 &&
      !this.config.allowedExtensions.includes(ext)
    ) {
      return true;
    }

    return false;
  }

  /** Get file extension including the dot */
  private getExtension(fileName: string): string {
    const lastDot = fileName.lastIndexOf(".");
    if (lastDot === -1) return "";
    return fileName.substring(lastDot).toLowerCase();
  }

  /** Filter tree items recursively */
  filterTree(items: TreeItem[]): TreeItem[] {
    return (
      items
        .filter((item) => !this.isHidden(item))
        // No longer filter by extension - show all files, mark non-allowed as inactive
        .map((item) => {
          if (item.type === "directory" && item.children) {
            return {
              ...item,
              children: this.filterTree(item.children),
            };
          }
          return item;
        })
      // Keep all directories (including empty ones) for consistent mental model
      // Empty directories are useful landmarks and may be needed for file creation
    );
  }

  /** Get the current mode */
  getMode(): WorkspaceMode {
    return this.config.mode;
  }

  /** Get filter configuration */
  getConfig(): FilterConfig {
    return this.config;
  }

  /** Update allowed extensions */
  setAllowedExtensions(extensions: string[]): void {
    this.config.allowedExtensions = extensions;
  }

  /** Update disabled extensions */
  setDisabledExtensions(extensions: string[]): void {
    this.config.disabledExtensions = extensions;
  }

  /** Update hidden patterns */
  setHiddenPatterns(patterns: string[]): void {
    this.config.hiddenPatterns = patterns;
  }

  /** Set whether dotfiles are shown */
  setShowHidden(show: boolean): void {
    this.showHidden = show;
  }

  /** Get whether dotfiles are shown */
  getShowHidden(): boolean {
    return this.showHidden;
  }

  /** Set whether module-specific filtering is enabled */
  setModuleFilterEnabled(enabled: boolean): void {
    this.moduleFilterEnabled = enabled;
  }

  /** Get whether module-specific filtering is enabled */
  getModuleFilterEnabled(): boolean {
    return this.moduleFilterEnabled;
  }

  /** Switch the active filtering mode at runtime */
  setMode(mode: WorkspaceMode): void {
    const centralExtensions = ALLOW_EXTENSIONS[mode];
    const defaultAllowedExtensions =
      centralExtensions === "all" ? [] : centralExtensions;
    const defaultHiddenPatterns = DENY_DIRECTORIES[mode] || [];
    const legacyDefaults = MODE_FILTERS[mode] || MODE_FILTERS.all;

    this.config = {
      mode,
      allowedExtensions: defaultAllowedExtensions,
      disabledExtensions: legacyDefaults.disabledExtensions ?? [],
      hiddenPatterns: defaultHiddenPatterns,
    };
  }
}
