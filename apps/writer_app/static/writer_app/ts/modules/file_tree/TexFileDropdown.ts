/**
 * TeX File Dropdown Manager
 * Handles section dropdown population and management
 */

import { FileTreeNode, TeXSection } from "./types.js";

export class TexFileDropdown {
  private dropdownId?: string;
  private onSectionSelect: (sectionId: string, sectionName: string) => void;

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

  constructor(
    dropdownId: string | undefined,
    onSectionSelect: (sectionId: string, sectionName: string) => void
  ) {
    this.dropdownId = dropdownId;
    this.onSectionSelect = onSectionSelect;
  }

  /**
   * Populate the section dropdown selector
   */
  public async populate(docType: string = "manuscript"): Promise<void> {
    if (!this.dropdownId) return;

    const dropdown = document.getElementById(
      this.dropdownId
    ) as HTMLSelectElement;
    if (!dropdown) {
      console.warn("[FileTree] Dropdown element not found:", this.dropdownId);
      return;
    }

    dropdown.innerHTML = "";

    try {
      const response = await fetch("/writer/api/sections-config/");
      const data = await response.json();

      if (!data.success || !data.hierarchy) {
        console.error("[FileTree] Failed to load sections hierarchy");
        this.populateFallback(dropdown, docType);
        return;
      }

      const hierarchy = data.hierarchy;

      if (docType === "shared" && hierarchy.shared) {
        this.addSections(dropdown, "Shared", hierarchy.shared.sections);
      } else if (docType === "manuscript" && hierarchy.manuscript) {
        this.addSections(dropdown, "Manuscript", hierarchy.manuscript.sections);
      } else if (docType === "supplementary" && hierarchy.supplementary) {
        this.addSections(
          dropdown,
          "Supplementary",
          hierarchy.supplementary.sections
        );
      } else if (docType === "revision" && hierarchy.revision) {
        this.addSections(dropdown, "Revision", hierarchy.revision.sections);
      } else {
        console.warn("[FileTree] Unknown document type:", docType);
        this.populateFallback(dropdown, docType);
        return;
      }

      console.log(
        "[FileTree] Populated dropdown with hierarchical sections for",
        docType
      );

      // Select first option if nothing selected
      if (dropdown.options.length > 0 && !dropdown.value) {
        dropdown.selectedIndex = 0;
        const firstOption = dropdown.options[0];
        console.log("[FileTree] Auto-selected first section:", firstOption.value);
        this.onSectionSelect(firstOption.value, firstOption.textContent || "");
      }

      // Add change event listener
      if (!dropdown.dataset.listenerAttached) {
        dropdown.addEventListener("change", (e) => {
          const target = e.target as HTMLSelectElement;
          if (target.value) {
            const sectionId = target.value;
            const selectedOption = target.options[target.selectedIndex];
            const sectionName = selectedOption.textContent || sectionId;
            this.onSectionSelect(sectionId, sectionName);
          }
        });
        dropdown.dataset.listenerAttached = "true";
      }
    } catch (error) {
      console.error("[FileTree] Error loading sections:", error);
      this.populateFallback(dropdown, docType);
    }
  }

  /**
   * Add sections to dropdown with optgroup
   */
  private addSections(
    dropdown: HTMLSelectElement,
    groupLabel: string,
    sections: any[]
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
   * Fallback population method
   */
  private populateFallback(
    dropdown: HTMLSelectElement,
    docType: string
  ): void {
    const sections = this.sectionsByDocType[docType] || [];

    if (sections.length === 0) {
      console.warn(
        "[FileTree] No sections available for document type:",
        docType
      );
      return;
    }

    const optgroup = document.createElement("optgroup");
    optgroup.label = docType.charAt(0).toUpperCase() + docType.slice(1);

    sections.forEach((sectionId) => {
      const option = document.createElement("option");
      option.value = sectionId;
      option.textContent = this.sectionNames[sectionId] || sectionId;
      optgroup.appendChild(option);
    });

    dropdown.appendChild(optgroup);
  }

  /**
   * Extract tex files from tree
   */
  public extractTexFiles(
    nodes: FileTreeNode[],
    files: Array<{ path: string; name: string }> = []
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
}
