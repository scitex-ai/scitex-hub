/**
 * WriterTreeSync - Synchronizes dropdown selectors with file tree
 *
 * Handles bidirectional synchronization:
 * 1. Doctype dropdown -> Tree focus (expand/collapse directories)
 * 2. Section dropdown -> Tree selection (scroll to and select file)
 * 3. Tree selection -> Dropdown updates (update both dropdowns)
 */

import { doctypeToDirectory, getDoctypeFromPath } from "../config/doctype-config";

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
   */
  private setupEventListeners(): void {
    // Listen for section dropdown item clicks
    this.config.sectionDropdown?.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      const sectionItem = target.closest(".section-item") as HTMLElement;

      if (sectionItem) {
        const sectionId = sectionItem.dataset.sectionId;
        if (sectionId) {
          console.log("[WriterTreeSync] Section dropdown clicked:", sectionId);
          this.syncTreeFromSection(sectionId);
        }
      }
    });
  }

  /**
   * Sync tree focus when doctype changes
   * Called from DoctypeChangeHandler
   */
  syncTreeFromDoctype(doctype: string): void {
    const tree = this.config.treeInstance;
    if (!tree) {
      console.log("[WriterTreeSync] No tree instance, skipping doctype sync");
      return;
    }

    const doctypeFolder = doctypeToDirectory[doctype];
    if (!doctypeFolder) {
      console.warn("[WriterTreeSync] Unknown doctype:", doctype);
      return;
    }

    console.log("[WriterTreeSync] Syncing tree to doctype folder:", doctypeFolder);

    // Use the tree's focusDirectory method to expand and scroll to the folder
    if (tree.focusDirectory) {
      tree.focusDirectory(doctypeFolder);
    } else if (tree.expandToPath) {
      // Fallback to expandToPath if focusDirectory not available
      tree.expandToPath(doctypeFolder);
    }
  }

  /**
   * Sync tree selection when section is selected from dropdown
   */
  syncTreeFromSection(sectionId: string): void {
    const tree = this.config.treeInstance;
    if (!tree) {
      console.log("[WriterTreeSync] No tree instance, skipping section sync");
      return;
    }

    // Section ID format: "manuscript/abstract" or "shared/authors"
    const [doctype, sectionName] = sectionId.split("/");
    if (!doctype || !sectionName) {
      console.warn("[WriterTreeSync] Invalid section ID format:", sectionId);
      return;
    }

    // Build the full file path
    const doctypeFolder = doctypeToDirectory[doctype];
    if (!doctypeFolder) {
      console.warn("[WriterTreeSync] Unknown doctype in section ID:", doctype);
      return;
    }

    // Determine the section file path
    let sectionPath: string;
    if (doctype === "shared") {
      // Shared sections are directly in 00_shared
      sectionPath = `${doctypeFolder}/${sectionName}.tex`;
    } else {
      // Other sections are in contents/ subdirectory
      sectionPath = `${doctypeFolder}/contents/${sectionName}.tex`;
    }

    console.log("[WriterTreeSync] Syncing tree to section path:", sectionPath);

    // Prevent infinite loop by checking if we already synced this path
    if (this.lastSyncedPath === sectionPath) {
      console.log("[WriterTreeSync] Already synced to this path, skipping");
      return;
    }
    this.lastSyncedPath = sectionPath;

    // Expand to the path and select it
    if (tree.selectFile) {
      tree.selectFile(sectionPath);
    } else if (tree.expandToPath) {
      tree.expandToPath(sectionPath);
    }

    // Clear the sync lock after a short delay
    setTimeout(() => {
      this.lastSyncedPath = null;
    }, 100);
  }

  /**
   * Sync dropdowns when a file is selected in the tree
   * Called from the file select handler
   */
  syncDropdownsFromTree(filePath: string): void {
    // Prevent infinite loop
    if (this.lastSyncedPath === filePath) {
      console.log("[WriterTreeSync] Already synced from this path, skipping dropdown update");
      return;
    }

    console.log("[WriterTreeSync] Syncing dropdowns from tree selection:", filePath);

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
  private updateSectionDropdownDisplay(sectionId: string, sectionName: string): void {
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
      console.log("[WriterTreeSync] Section not in dropdown, showing name:", sectionName);
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
  focusTreePath(path: string): void {
    const tree = this.config.treeInstance;
    if (!tree) return;

    if (tree.expandToPath) {
      tree.expandToPath(path);
    }

    // Scroll the path into view
    setTimeout(() => {
      const treeElement = document.querySelector(`[data-path="${path}"]`);
      if (treeElement) {
        treeElement.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 100);
  }
}

// Singleton instance for global access
let writerTreeSyncInstance: WriterTreeSync | null = null;

/**
 * Initialize the WriterTreeSync singleton
 */
export function initWriterTreeSync(config: WriterTreeSyncConfig): WriterTreeSync {
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
