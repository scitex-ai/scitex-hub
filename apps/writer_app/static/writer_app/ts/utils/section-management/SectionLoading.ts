/**
 * Section Loading Module
 * Handles loading section content from API and switching between sections
 */

import type { WriterEditor, SectionsManager, PDFPreviewManager } from "../../modules/index.js";
import { setLoadingContent } from "../../modules/index.js";
import { getWriterConfig } from "../../helpers.js";
import { getUserContext } from "../ui.js";
import { syncDropdownToSection } from "../section-dropdown/index.js";
import { updateSectionUI } from "./SectionUI.js";

/**
 * Load section content from API
 */
export async function loadSectionContent(
  editor: WriterEditor,
  sectionsManager: SectionsManager,
  _state: any,
  sectionId: string,
  pdfPreviewManager?: PDFPreviewManager,
): Promise<void> {
  const config = getWriterConfig();
  if (!config.projectId) {
    console.warn("[Writer] Cannot load section content: no project ID");
    return;
  }

  try {
    // Extract section name and doc type from sectionId (e.g., "manuscript/abstract" -> doc_type="manuscript", section_name="abstract")
    const parts = sectionId.split("/");
    if (parts.length !== 2) {
      console.warn("[Writer] Invalid section ID format:", sectionId);
      return;
    }

    const docType = parts[0];
    const sectionName = parts[1];

    const userContext = getUserContext();
    console.log(
      `${userContext} [Writer] Loading section content:`,
      sectionId,
      "docType:",
      docType,
      "sectionName:",
      sectionName,
    );

    const response = await fetch(
      `/writer/api/project/${config.projectId}/section/${sectionName}/?doc_type=${docType}`,
    );

    if (!response.ok) {
      const error = await response.text();
      console.error("[Writer] Failed to load section:", response.status, error);
      return;
    }

    const data = await response.json();
    console.log("[Writer] API Response for", sectionId, ":", data);

    if (data.success && data.content !== undefined) {
      console.log(
        "[Writer] ✓ Content loaded for:",
        sectionId,
        "length:",
        data.content.length,
      );
      console.log("[Writer] First 100 chars:", data.content.substring(0, 100));

      // Set flag to prevent multiple auto-compiles during onChange events
      setLoadingContent(true);
      sectionsManager.setContent(sectionId, data.content);

      // Use setContentForSection to restore cursor position
      if (typeof (editor as any).setContentForSection === "function") {
        (editor as any).setContentForSection(sectionId, data.content);
      } else {
        editor.setContent(data.content);
      }

      // Reset flag and trigger ONE initial preview
      setTimeout(() => {
        setLoadingContent(false);
        // Trigger initial preview for the loaded section (skip for compiled sections)
        const isCompiledSection =
          sectionId.endsWith("/compiled_pdf") ||
          sectionId.endsWith("/compiled_tex");
        if (pdfPreviewManager && !isCompiledSection) {
          console.log("[Writer] Triggering initial preview for:", sectionId);
          pdfPreviewManager.compileQuick(data.content, sectionId);
        }
      }, 100);
    } else {
      const errorMsg = data.error || "Unknown error loading section";
      console.error("[Writer] ✗ API Error:", errorMsg);
      throw new Error(errorMsg);
    }
  } catch (error) {
    console.error("[Writer] Error loading section content:", error);
    setLoadingContent(false); // Reset flag on error
    throw error; // Re-throw to let caller handle it
  }
}

/**
 * Switch to a section
 */
export async function switchSection(
  editor: WriterEditor,
  sectionsManager: SectionsManager,
  state: any,
  sectionId: string,
  pdfPreviewManager?: PDFPreviewManager,
): Promise<void> {
  // Save current section
  const currentContent = editor.getContent();
  sectionsManager.setContent(state.currentSection, currentContent);

  // Update current section
  state.currentSection = sectionId;
  console.log("[Writer] Switching to section:", sectionId);

  // Open section in file tab manager (mimic /code/ page behavior)
  const fileTabManager = (window as any).writerFileTabManager;
  if (fileTabManager) {
    // Extract section name for display (e.g., "manuscript/abstract" -> "Abstract")
    const parts = sectionId.split("/");
    const sectionName = parts.length > 1 ? parts[1] : sectionId;
    const displayName = sectionName.charAt(0).toUpperCase() + sectionName.slice(1);
    fileTabManager.openFile(sectionId, displayName);
  }

  updateSectionUI(sectionId);
  syncDropdownToSection(sectionId);

  // For compiled_pdf sections, load the compiled TeX in editor (read-only)
  if (sectionId.endsWith("/compiled_pdf")) {
    console.log("[Writer] Compiled PDF section - loading compiled TeX");

    // Set editor to read-only
    if (typeof (editor as any).setReadOnly === "function") {
      (editor as any).setReadOnly(true);
    }

    // Load compiled_tex content
    const compiledTexId = sectionId.replace("/compiled_pdf", "/compiled_tex");
    try {
      await loadSectionContent(editor, sectionsManager, state, compiledTexId, pdfPreviewManager);
    } catch (error) {
      const errorMsg = `Failed to load compiled TeX: ${error}`;
      console.error("[Writer]", errorMsg);
      editor.setContent(
        `% ERROR: ${errorMsg}\n% Please check browser console for details`,
      );
    }
    return;
  }

  // For regular editable sections
  if (typeof (editor as any).setReadOnly === "function") {
    (editor as any).setReadOnly(false);
  }

  // Load fresh content from API
  try {
    await loadSectionContent(editor, sectionsManager, state, sectionId, pdfPreviewManager);
  } catch (error) {
    const errorMsg = `Failed to load section ${sectionId}: ${error}`;
    console.error("[Writer]", errorMsg);
    editor.setContent(
      `% ERROR: ${errorMsg}\n% Please check browser console for details`,
    );
  }
}

/**
 * Setup section listeners
 */
export function setupSectionListeners(
  sectionsManager: SectionsManager,
  editor: WriterEditor,
  state: any,
  _storage: any,
): void {
  const sectionItems = document.querySelectorAll(".section-tab");
  sectionItems.forEach((item) => {
    item.addEventListener("click", (e: Event) => {
      const target = e.target as HTMLElement;
      const sectionId = target.dataset.section;
      if (sectionId) {
        switchSection(editor, sectionsManager, state, sectionId);
      }
    });
  });

  // NO CALLBACKS - direct error handling only
}
