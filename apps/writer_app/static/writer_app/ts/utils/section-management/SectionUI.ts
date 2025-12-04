/**
 * Section UI Module
 * Handles UI updates for sections including title labels, PDF preview, and compiled PDF display
 */

import { getWriterConfig } from "../../helpers.js";
import {
  updateSectionTitleLabel,
  updatePDFPreviewTitle,
  updateCommitButtonVisibility,
} from "../ui.js";

// Module-level variables
let compileTimeout: ReturnType<typeof setTimeout> | null = null;

/**
 * Clear compile timeout
 */
export function clearCompileTimeout(): void {
  if (compileTimeout) {
    clearTimeout(compileTimeout);
    compileTimeout = null;
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
    "[Writer] Loading compiled PDF for section:",
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
      console.error("[Writer] Error checking compiled PDF:", error);
      textPreview.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 2rem; text-align: center; color: var(--color-fg-muted);">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3 text-warning"></i>
                    <h5 style="color: var(--color-fg-default);">Error Loading PDF</h5>
                    <p>Could not check if PDF exists. Please try again.</p>
                </div>
            `;
    });
}
