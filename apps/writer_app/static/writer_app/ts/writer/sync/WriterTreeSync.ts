/**
 * WriterTreeSync - Synchronizes dropdown selectors with file tree
 *
 * Handles bidirectional synchronization:
 * 1. Doctype dropdown -> Tree focus (expand/collapse directories)
 * 2. Section dropdown -> Tree selection (scroll to and select file)
 * 3. Tree selection -> Dropdown updates (update both dropdowns)
 */

import { getDoctypeFromPath } from "../config/doctype-config";

console.log("[DEBUG] WriterTreeSync.ts loaded");

export interface WriterTreeSyncConfig {
  doctypeSelector: HTMLSelectElement;
  sectionDropdown: HTMLElement;
  sectionText: HTMLElement;
  treeInstance: any; // WorkspaceFilesTree instance
}

export class WriterTreeSync {
  private config: WriterTreeSyncConfig;
  private lastSyncedPath: string | null = null;

  constructor(config: WriterTreeSyncConfig) {
    this.config = config;
    this.setupEventListeners();
    console.log("[WriterTreeSync] Initialized with config:", {
      hasDoctype: !!config.doctypeSelector,
      hasSectionDropdown: !!config.sectionDropdown,
      hasTree: !!config.treeInstance,
    });
  }

  /**
   * Setup event listeners for synchronization
   * Note: Editor->tree sync disabled since tree is shared across modules
   */
  private setupEventListeners(): void {
    // Tree is shared across modules - do not auto-navigate it from editor
  }

  /**
   * Sync tree focus when doctype changes
   * Called from DoctypeChangeHandler
   */
  syncTreeFromDoctype(_doctype: string): void {
    // Editor->tree sync disabled: tree is shared across modules
  }

  /**
   * Sync tree selection when section is selected from dropdown
   */
  syncTreeFromSection(_sectionId: string): void {
    // Editor->tree sync disabled: tree is shared across modules
  }

  /**
   * Sync dropdowns when a file is selected in the tree
   * Called from the file select handler
   */
  syncDropdownsFromTree(filePath: string): void {
    // Prevent infinite loop
    if (this.lastSyncedPath === filePath) {
      console.log(
        "[WriterTreeSync] Already synced from this path, skipping dropdown update",
      );
      return;
    }

    console.log(
      "[WriterTreeSync] Syncing dropdowns from tree selection:",
      filePath,
    );

    // Extract doctype from path
    const doctype = getDoctypeFromPath(filePath);
    if (doctype) {
      // Update doctype selector if different
      if (this.config.doctypeSelector.value !== doctype) {
        this.config.doctypeSelector.value = doctype;
        console.log("[WriterTreeSync] Updated doctype selector to:", doctype);

        // Dispatch change event to trigger section dropdown update
        this.config.doctypeSelector.dispatchEvent(new Event("change"));
      }
    }

    // Extract section name from path
    const fileName = filePath.split("/").pop();
    if (fileName?.endsWith(".tex")) {
      const sectionName = fileName.replace(".tex", "");
      const sectionId = doctype ? `${doctype}/${sectionName}` : null;

      if (sectionId) {
        this.updateSectionDropdownDisplay(sectionId, sectionName);
      }
    }
  }

  /**
   * Update the section dropdown display to show the selected section
   */
  private updateSectionDropdownDisplay(
    sectionId: string,
    sectionName: string,
  ): void {
    const dropdownContainer = this.config.sectionDropdown;
    const selectorText = this.config.sectionText;

    if (!dropdownContainer || !selectorText) return;

    // Find and highlight the matching section item
    const sectionItems = dropdownContainer.querySelectorAll(".section-item");
    let found = false;
    let pageNum = 1;

    sectionItems.forEach((item, index) => {
      const itemSectionId = (item as HTMLElement).dataset.sectionId;

      if (itemSectionId === sectionId) {
        // Mark this as active
        sectionItems.forEach((si) => si.classList.remove("active"));
        item.classList.add("active");
        found = true;
        pageNum = index + 1;

        // Get the display name from the item
        const itemName =
          item.querySelector(".section-item-name")?.textContent ||
          sectionName.replace(/_/g, " ");
        selectorText.textContent = `${pageNum}. ${itemName}`;

        console.log("[WriterTreeSync] Updated section dropdown to:", sectionId);
      }
    });

    if (!found) {
      // Section not in current dropdown - just update display text
      selectorText.textContent = sectionName.replace(/_/g, " ");
      console.log(
        "[WriterTreeSync] Section not in dropdown, showing name:",
        sectionName,
      );
    }
  }

  /**
   * Get the current doctype from the selector
   */
  getCurrentDoctype(): string {
    return this.config.doctypeSelector?.value || "manuscript";
  }

  /**
   * Focus tree on a specific path without selecting it
   */
  focusTreePath(_path: string): void {
    // Editor->tree sync disabled: tree is shared across modules
  }
}

// Singleton instance for global access
let writerTreeSyncInstance: WriterTreeSync | null = null;

/**
 * Initialize the WriterTreeSync singleton
 */
export function initWriterTreeSync(
  config: WriterTreeSyncConfig,
): WriterTreeSync {
  writerTreeSyncInstance = new WriterTreeSync(config);
  (window as any).writerTreeSync = writerTreeSyncInstance;
  return writerTreeSyncInstance;
}

/**
 * Get the WriterTreeSync singleton instance
 */
export function getWriterTreeSync(): WriterTreeSync | null {
  return writerTreeSyncInstance || (window as any).writerTreeSync;
}
