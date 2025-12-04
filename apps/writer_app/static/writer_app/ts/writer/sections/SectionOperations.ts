/**
 * Section Operations Module
 * Handles section loading, switching, and UI updates
 */

import {
  WriterEditor,
  setLoadingContent,
} from "../../modules/index.js";
import {
  showToast,
  getUserContext,
  updateSectionTitleLabel,
  updatePDFPreviewTitle,
  updateCommitButtonVisibility,
  syncDropdownToSection,
} from "../../utils/index.js";
import { getWriterConfig } from "../../helpers.js";

let modulePdfPreviewManager: any = null;
let compileTimeout: ReturnType<typeof setTimeout> | null = null;

/**
 * Set the module-level PDF preview manager reference
 */
export function setPdfPreviewManager(manager: any): void {
  modulePdfPreviewManager = manager;
}

/**
 * Clear the compile timeout
 */
export function clearCompileTimeout(): void {
  if (compileTimeout) {
    clearTimeout(compileTimeout);
    compileTimeout = null;
  }
}

/**
 * Load section content from API
 */
export async function loadSectionContent(
  editor: WriterEditor,
  sectionsManager: any,
  _state: any,
  sectionId: string,
): Promise<void> {
  const config = getWriterConfig();
  if (!config.projectId) {
    console.warn(
      "[SectionOperations] Cannot load section content: no project ID",
    );
    return;
  }

  try {
    // Extract section name and doc type from sectionId (e.g., "manuscript/abstract" -> doc_type="manuscript", section_name="abstract")
    const parts = sectionId.split("/");
    if (parts.length !== 2) {
      console.warn(
        "[SectionOperations] Invalid section ID format:",
        sectionId,
      );
      return;
    }

    const docType = parts[0];
    const sectionName = parts[1];

    const userContext = getUserContext();
    console.log(
      `${userContext} [SectionOperations] Loading section content:`,
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
      console.error(
        "[SectionOperations] Failed to load section:",
        response.status,
        error,
      );
      return;
    }

    const data = await response.json();
    console.log("[SectionOperations] API Response for", sectionId, ":", data);

    if (data.success && data.content !== undefined) {
      console.log(
        "[SectionOperations] ✓ Content loaded for:",
        sectionId,
        "length:",
        data.content.length,
      );
      console.log(
        "[SectionOperations] First 100 chars:",
        data.content.substring(0, 100),
      );

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
        if (modulePdfPreviewManager && !isCompiledSection) {
          console.log(
            "[SectionOperations] Triggering initial preview for:",
            sectionId,
          );
          modulePdfPreviewManager.compileQuick(data.content, sectionId);
        }
      }, 100);
    } else {
      const errorMsg = data.error || "Unknown error loading section";
      console.error("[SectionOperations] ✗ API Error:", errorMsg);
      throw new Error(errorMsg);
    }
  } catch (error) {
    console.error(
      "[SectionOperations] Error loading section content:",
      error,
    );
    setLoadingContent(false); // Reset flag on error
    throw error; // Re-throw to let caller handle it
  }
}

/**
 * Switch to a section
 */
export async function switchSection(
  editor: WriterEditor,
  sectionsManager: any,
  state: any,
  sectionId: string,
): Promise<void> {
  // Save current section
  const currentContent = editor.getContent();
  sectionsManager.setContent(state.currentSection, currentContent);

  // Update current section
  state.currentSection = sectionId;
  console.log("[SectionOperations] Switching to section:", sectionId);

  updateSectionUI(sectionId);
  syncDropdownToSection(sectionId);

  // For compiled_pdf sections, load the compiled TeX in editor (read-only)
  if (sectionId.endsWith("/compiled_pdf")) {
    console.log(
      "[SectionOperations] Compiled PDF section - loading compiled TeX",
    );

    // Set editor to read-only
    if (typeof (editor as any).setReadOnly === "function") {
      (editor as any).setReadOnly(true);
    }

    // Load compiled_tex content
    const compiledTexId = sectionId.replace("/compiled_pdf", "/compiled_tex");
    try {
      await loadSectionContent(editor, sectionsManager, state, compiledTexId);
    } catch (error) {
      const errorMsg = `Failed to load compiled TeX: ${error}`;
      console.error("[SectionOperations]", errorMsg);
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
    await loadSectionContent(editor, sectionsManager, state, sectionId);
  } catch (error) {
    const errorMsg = `Failed to load section ${sectionId}: ${error}`;
    console.error("[SectionOperations]", errorMsg);
    editor.setContent(
      `% ERROR: ${errorMsg}\n% Please check browser console for details`,
    );
  }
}

/**
 * Update section UI
 */
export function updateSectionUI(sectionId: string): void {
  document.querySelectorAll(".section-tab").forEach((tab) => {
    tab.classList.toggle(
      "active",
      (tab as HTMLElement).dataset.section === sectionId,
    );
  });

  // Update the section title label in the editor header
  updateSectionTitleLabel(sectionId);

  // Update PDF preview title as well
  updatePDFPreviewTitle(sectionId);

  // Show/hide commit button based on section type (hide for read-only sections)
  updateCommitButtonVisibility(sectionId);

  // Load compiled PDF if this is the compiled_pdf section
  if (sectionId.endsWith("/compiled_pdf")) {
    // Cancel any pending auto-compile from previous section
    clearCompileTimeout();
    loadCompiledPDF(sectionId);
  }
}

/**
 * Load compiled PDF for display (not quick preview)
 */
export function loadCompiledPDF(sectionId: string): void {
  const config = getWriterConfig();
  if (!config.projectId) return;

  // Extract doc type from sectionId (e.g., "manuscript/compiled_pdf" -> "manuscript")
  const parts = sectionId.split("/");
  const docType = parts[0];

  // Use API endpoint for PDF with doc_type query parameter
  const pdfUrl = `/writer/api/project/${config.projectId}/pdf/?doc_type=${docType}`;

  console.log(
    "[SectionOperations] Loading compiled PDF for section:",
    sectionId,
    "URL:",
    pdfUrl,
  );

  const textPreview = document.getElementById("text-preview");
  if (!textPreview) return;

  // Check if PDF exists first
  fetch(pdfUrl, { method: "HEAD" })
    .then((response) => {
      if (!response.ok) {
        // PDF doesn't exist - show helpful message
        textPreview.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 2rem; text-align: center; color: var(--color-fg-muted);">
                        <i class="fas fa-file-pdf fa-3x mb-3" style="opacity: 0.3;"></i>
                        <h5 style="color: var(--color-fg-default);">Full Manuscript Not Compiled Yet</h5>
                        <p style="margin: 1rem 0;">Click the 📄 <strong>Compile</strong> button in the dropdown to generate the full manuscript PDF.</p>
                        <small style="opacity: 0.7;">This combines all enabled sections into a single document.</small>
                    </div>
                `;
        return;
      }

      // PDF exists - display it with cache-busting
      const cacheBustUrl = `${pdfUrl}?t=${Date.now()}`;
      textPreview.innerHTML = `
                <div class="pdf-preview-container">
                    <div class="pdf-preview-viewer" id="pdf-viewer-pane">
                        <iframe
                            src="${cacheBustUrl}#toolbar=0&navpanes=0&scrollbar=1&view=FitW&zoom=page-width"
                            type="application/pdf"
                            width="100%"
                            height="100%"
                            title="Compiled PDF"
                            frameborder="0"
                            style="display: block;">
                        </iframe>
                    </div>
                </div>
            `;

      // Reset scroll position to top
      textPreview.scrollTop = 0;
    })
    .catch((error) => {
      console.error(
        "[SectionOperations] Error checking compiled PDF:",
        error,
      );
      textPreview.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 2rem; text-align: center; color: var(--color-fg-muted);">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3 text-warning"></i>
                    <h5 style="color: var(--color-fg-default);">Error Loading PDF</h5>
                    <p>Could not check if PDF exists. Please try again.</p>
                </div>
            `;
    });
}
