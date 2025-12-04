/**
 * Section Dropdown Manager Module
 * Handles population and management of section dropdowns for different document types
 */

import { FileTreeNode } from "../file_tree.js";

export interface SectionConfig {
  id: string;
  label: string;
  optional?: boolean;
  view_only?: boolean;
}

export interface DocTypeHierarchy {
  sections: SectionConfig[];
}

export interface SectionsHierarchy {
  [key: string]: DocTypeHierarchy;
  shared?: DocTypeHierarchy;
  manuscript?: DocTypeHierarchy;
  supplementary?: DocTypeHierarchy;
  revision?: DocTypeHierarchy;
}

export class SectionDropdownManager {
  /**
   * Map of section IDs to readable names (IMRAD structure)
   */
  private sectionNames: { [key: string]: string } = {
    title: "Title",
    abstract: "Abstract",
    introduction: "Introduction",
    methods: "Methods",
    results: "Results",
    discussion: "Discussion",
    conclusion: "Conclusion",
    references: "References",
    keywords: "Keywords",
    authors: "Authors",
    highlights: "Highlights",
    graphical_abstract: "Graphical Abstract",
  };

  /**
   * Sections available for each document type
   */
  private sectionsByDocType: { [key: string]: string[] } = {
    manuscript: [
      "abstract",
      "introduction",
      "methods",
      "results",
      "discussion",
      "conclusion",
      "references",
    ],
    supplementary: ["content", "methods", "results"],
    revision: ["response", "changes"],
    shared: [],
  };

  /**
   * Extract all .tex files from the tree recursively
   */
  public extractTexFiles(
    nodes: FileTreeNode[],
    files: Array<{ path: string; name: string }> = [],
  ): Array<{ path: string; name: string }> {
    nodes.forEach((node) => {
      if (node.type === "file" && node.name.endsWith(".tex")) {
        files.push({ path: node.path, name: node.name });
      } else if (node.type === "directory" && node.children) {
        this.extractTexFiles(node.children, files);
      }
    });
    return files;
  }

  /**
   * Populate the section dropdown selector with hierarchical structure
   */
  public async populateTexFileDropdown(
    dropdownId: string,
    docType: string = "manuscript",
    onFileSelect?: (filePath: string, fileName: string) => void,
  ): Promise<void> {
    const dropdown = document.getElementById(
      dropdownId,
    ) as HTMLSelectElement | null;
    if (!dropdown) {
      console.warn("[SectionDropdown] Dropdown element not found:", dropdownId);
      return;
    }

    // Clear existing options
    dropdown.innerHTML = "";

    try {
      // Fetch hierarchical sections configuration
      const response = await fetch("/writer/api/sections-config/");
      const data = await response.json();

      if (!data.success || !data.hierarchy) {
        console.error("[SectionDropdown] Failed to load sections hierarchy");
        this.populateTexFileDropdownFallback(dropdown, docType);
        return;
      }

      const hierarchy: SectionsHierarchy = data.hierarchy;

      // Populate dropdown based on docType
      if (docType === "shared" && hierarchy.shared) {
        this.addSectionsToDropdown(
          dropdown,
          "Shared",
          hierarchy.shared.sections,
        );
      } else if (docType === "manuscript" && hierarchy.manuscript) {
        this.addSectionsToDropdown(
          dropdown,
          "Manuscript",
          hierarchy.manuscript.sections,
        );
      } else if (docType === "supplementary" && hierarchy.supplementary) {
        this.addSectionsToDropdown(
          dropdown,
          "Supplementary",
          hierarchy.supplementary.sections,
        );
      } else if (docType === "revision" && hierarchy.revision) {
        this.addSectionsToDropdown(
          dropdown,
          "Revision",
          hierarchy.revision.sections,
        );
      } else {
        console.warn("[SectionDropdown] Unknown document type:", docType);
        this.populateTexFileDropdownFallback(dropdown, docType);
        return;
      }

      console.log(
        "[SectionDropdown] Populated dropdown with hierarchical sections for",
        docType,
      );

      // Select the first option by default if nothing is selected
      if (dropdown.options.length > 0 && !dropdown.value) {
        dropdown.selectedIndex = 0;
        const firstOption = dropdown.options[0];
        console.log(
          "[SectionDropdown] Auto-selected first section:",
          firstOption.value,
        );
        // Trigger the selection to load the content
        if (onFileSelect) {
          onFileSelect(firstOption.value, firstOption.textContent || "");
        }
      }

      // Add change event listener if not already attached
      if (!dropdown.dataset.listenerAttached) {
        dropdown.addEventListener("change", (e) => {
          const target = e.target as HTMLSelectElement;
          if (target.value && onFileSelect) {
            const sectionId = target.value;
            const selectedOption = target.options[target.selectedIndex];
            const sectionName = selectedOption.textContent || sectionId;

            // Trigger callback with section info
            onFileSelect(sectionId, sectionName);
          }
        });
        dropdown.dataset.listenerAttached = "true";
      }
    } catch (error) {
      console.error("[SectionDropdown] Error loading sections:", error);
      this.populateTexFileDropdownFallback(dropdown, docType);
    }
  }

  /**
   * Add sections to dropdown with optgroup
   */
  private addSectionsToDropdown(
    dropdown: HTMLSelectElement,
    groupLabel: string,
    sections: SectionConfig[],
  ): void {
    if (sections.length === 0) return;

    const optgroup = document.createElement("optgroup");
    optgroup.label = groupLabel;

    sections.forEach((section) => {
      const option = document.createElement("option");
      option.value = section.id;
      option.textContent = section.label;

      if (section.optional) {
        option.textContent += " (Optional)";
      }
      if (section.view_only) {
        option.disabled = true;
        option.textContent += " (View Only)";
      }

      optgroup.appendChild(option);
    });

    dropdown.appendChild(optgroup);
  }

  /**
   * Fallback population method using legacy structure
   */
  private populateTexFileDropdownFallback(
    dropdown: HTMLSelectElement,
    docType: string,
  ): void {
    const sections = this.sectionsByDocType[docType] || [];

    if (sections.length === 0) {
      console.warn(
        "[SectionDropdown] No sections available for document type:",
        docType,
      );
      return;
    }

    sections.forEach((sectionId) => {
      const option = document.createElement("option");
      option.value = sectionId;
      option.textContent =
        this.sectionNames[sectionId] ||
        sectionId.charAt(0).toUpperCase() + sectionId.slice(1);
      dropdown.appendChild(option);
    });

    console.log(
      "[SectionDropdown] Used fallback to populate dropdown with",
      sections.length,
      "sections",
    );
  }
}
