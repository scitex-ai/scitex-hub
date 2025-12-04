/**
 * Auto-Save Module
 * Handles automatic saving and compilation scheduling
 */

import type { WriterEditor } from "./editor.js";
import type { SectionsManager } from "./sections.js";
import type { PDFPreviewManager } from "./pdf-preview/index.js";
import { getCsrfToken } from "@/utils/csrf.js";
import { getWriterConfig } from "../helpers.js";
import { getUserContext } from "../utils/ui.js";
import {
  validateSaveSectionsResponse,
  isSaveSectionsResponse,
} from "../types/api-responses.js";

let saveTimeout: ReturnType<typeof setTimeout>;
let compileTimeout: ReturnType<typeof setTimeout>;

// Flag to prevent auto-compile during content loading
let isLoadingContent: boolean = false;

/**
 * Set loading content flag (used externally)
 */
export function setLoadingContent(loading: boolean): void {
  isLoadingContent = loading;
}

/**
 * Get loading content flag
 */
export function getLoadingContent(): boolean {
  return isLoadingContent;
}

/**
 * Schedule auto-save
 */
export function scheduleSave(
  _editor: WriterEditor | null,
  sectionsManager: SectionsManager,
  state: any,
): void {
  clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    saveSections(sectionsManager, state);
  }, 5000); // Auto-save after 5 seconds of inactivity
}

/**
 * Schedule auto-compile for live PDF preview
 */
export function scheduleAutoCompile(
  pdfPreviewManager: PDFPreviewManager | null,
  content: string,
  sectionId?: string,
): void {
  if (!pdfPreviewManager) return;

  // Skip auto-compile if we're just loading content (not user editing)
  if (isLoadingContent) {
    console.log("[Writer] Skipping auto-compile during content load");
    return;
  }

  // Clear existing timeout
  clearTimeout(compileTimeout);

  // Schedule compilation after user stops typing
  compileTimeout = setTimeout(() => {
    console.log(
      "[Writer] Auto-compiling for live preview, section:",
      sectionId,
    );
    // Pass section ID for section-specific preview
    pdfPreviewManager.compileQuick(content, sectionId);
  }, 2000); // Wait 2 seconds after user stops typing
}

/**
 * Save sections
 */
export async function saveSections(
  sectionsManager: SectionsManager,
  state: any,
): Promise<void> {
  try {
    // Get project ID from page config
    const config = getWriterConfig();
    if (!config.projectId) {
      console.warn("[Writer] Cannot save sections: no project ID");
      return;
    }

    const allSections = sectionsManager.getAll(); // Returns Section[]

    // Build sections object with section IDs as keys
    const sections: Record<string, string> = {};
    for (const section of allSections) {
      const content = section.content || "";
      // Skip compiled sections (read-only, virtual sections)
      if (section.id && section.id.endsWith("/compiled_pdf")) {
        continue;
      }
      if (content.trim().length > 0 && section.id) {
        sections[section.id] = content; // Use section.id, not array index!
      }
    }

    if (Object.keys(sections).length === 0) {
      console.log("[Writer] No non-empty sections to save");
      return;
    }

    const userContext = getUserContext();
    console.log(
      `${userContext} [Writer] Saving ${Object.keys(sections).length} sections for ${state.currentDocType || "manuscript"}`,
    );

    const response = await fetch(
      `/writer/api/project/${config.projectId}/save-sections/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          sections: sections,
          doc_type: state.currentDocType || "manuscript",
        }),
      },
    );

    const data = await response.json();

    // Validate response format
    if (!isSaveSectionsResponse(data)) {
      console.error(
        "[Writer] Invalid save response format (missing fields):",
        data,
      );
      return;
    }

    // Validate response data (throws on error)
    try {
      validateSaveSectionsResponse(data);
    } catch (validationError) {
      console.error("[Writer] Save response failed validation:", validationError, data);
      return;
    }

    if (data.success) {
      console.log(
        `${userContext} [Writer] Sections saved successfully:`,
        data.sections_saved,
      );
    } else {
      console.error(
        `${userContext} [Writer] Failed to save some sections:`,
        data.errors,
      );
    }
  } catch (error) {
    console.error("[Writer] Error saving sections:", error);
  }
}
