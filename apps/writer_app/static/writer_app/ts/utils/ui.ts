/**
 * UI Utilities
 * Basic helper functions for UI interactions
 */

import { getWriterConfig } from "../helpers.js";

/**
 * Show toast notification
 */
export function showToast(message: string, _type: string = "info"): void {
  const fn = (window as any).showToast || ((msg: string) => console.log(msg));
  fn(message);
}

/**
 * Get user context string for logging
 */
export function getUserContext(): string {
  const config = getWriterConfig();
  if (config.visitorUsername) {
    return `[${config.visitorUsername}]`;
  } else if (config.username) {
    return `[${config.username}]`;
  }
  return "[visitor]";
}

/**
 * Update word count display
 */
export function updateWordCountDisplay(
  _section: string,
  count: number,
): void {
  const display = document.getElementById("current-word-count");
  if (display) {
    display.textContent = String(count);
  }
}

/**
 * Update the section title label to show current section name with file link
 */
export function updateSectionTitleLabel(sectionId: string): void {
  const titleElement = document.getElementById("editor-section-title");
  if (!titleElement) return;

  const config = getWriterConfig();

  // Extract section info from sectionId (e.g., "manuscript/abstract")
  const parts = sectionId.split("/");
  const docType = parts[0];
  const sectionName = parts[parts.length - 1];

  // Capitalize and format the section name
  const formattedName = sectionName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

  // Build file path for link
  const docDirMap: Record<string, string> = {
    manuscript: "01_manuscript",
    supplementary: "02_supplementary",
    revision: "03_revision",
    shared: "shared",
  };

  let filePath = "";
  if (sectionName === "compiled_pdf" || sectionName === "compiled_tex") {
    // For compiled_pdf, link to the TEX file (since that's what shows in editor)
    // Compiled files are in the root of doc directory
    filePath = `scitex/writer/${docDirMap[docType]}/${docType}.tex`;
  } else {
    // Regular sections are in contents/
    const ext =
      sectionName === "bibliography" || sectionName === "references"
        ? "bib"
        : "tex";
    if (docType === "shared") {
      filePath = `scitex/writer/00_shared/${sectionName}.${ext}`;
    } else {
      filePath = `scitex/writer/${docDirMap[docType]}/contents/${sectionName}.${ext}`;
    }
  }

  // Create link to project browser
  const fileLink =
    config.username && config.projectSlug
      ? `/${config.username}/${config.projectSlug}/blob/${filePath}`
      : "";

  if (fileLink) {
    titleElement.innerHTML = `${formattedName} Source <a href="${fileLink}" target="_blank" style="font-size: 0.8em; opacity: 0.7;">📁</a>`;
  } else {
    titleElement.textContent = `${formattedName} Source`;
  }
}

/**
 * Update the PDF preview panel title to show current section with link
 */
export function updatePDFPreviewTitle(sectionId: string): void {
  const titleElement = document.getElementById("preview-title");
  if (!titleElement) return;

  const config = getWriterConfig();

  // Extract section name from sectionId
  const parts = sectionId.split("/");
  const docType = parts[0];
  const sectionName = parts[parts.length - 1];

  // Capitalize and format
  const docTypeLabel = docType.charAt(0).toUpperCase() + docType.slice(1);
  const formattedName = sectionName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

  // Build PDF file link
  let pdfLink = "";
  if (sectionName === "compiled_pdf" && config.username && config.projectSlug) {
    // Link to compiled PDF
    const docDirMap: Record<string, string> = {
      manuscript: "01_manuscript",
      supplementary: "02_supplementary",
      revision: "03_revision",
    };
    pdfLink = `/${config.username}/${config.projectSlug}/blob/scitex/writer/${docDirMap[docType]}/${docType}.pdf`;
  } else if (config.username && config.projectSlug) {
    // Link to preview PDF
    pdfLink = `/${config.username}/${config.projectSlug}/blob/scitex/writer/preview_output/preview-${sectionName}.pdf`;
  }

  // Special case for compiled_pdf - don't add "PDF" twice
  let titleText = "";
  if (sectionName === "compiled_pdf") {
    titleText = `${docTypeLabel} PDF`;
  } else {
    titleText = `${docTypeLabel} ${formattedName} PDF`;
  }

  // Add link if available
  if (pdfLink) {
    titleElement.innerHTML = `${titleText} <a href="${pdfLink}" target="_blank" style="font-size: 0.8em; opacity: 0.7;">📁</a>`;
  } else {
    titleElement.textContent = titleText;
  }
}

/**
 * Update commit button state based on section type and user authentication
 * - Hides button for guest users (Visitor Mode)
 * - Disables button for read-only sections (keeps it visible to reduce surprise)
 */
export function updateCommitButtonVisibility(sectionId: string): void {
  const commitBtn = document.getElementById(
    "git-commit-btn",
  ) as HTMLButtonElement;
  if (!commitBtn) return;

  const config = (window as any).WRITER_CONFIG;

  // Hide for guest users (projectId === 0 means demo/guest project)
  if (!config || config.projectId === 0) {
    commitBtn.style.display = "none";
    return;
  }

  // Always show button for authenticated users
  commitBtn.style.display = "";

  // Extract section name from sectionId (e.g., "manuscript/compiled_pdf" -> "compiled_pdf")
  const parts = sectionId.split("/");
  const sectionName = parts[parts.length - 1];

  // Disable button for read-only sections (but keep it visible)
  // compiled_pdf is the merged/compiled document
  // figures, tables, references are directories or view-only sections
  const readOnlySections = ["compiled_pdf", "figures", "tables", "references"];
  const isReadOnly = readOnlySections.includes(sectionName);

  if (isReadOnly) {
    commitBtn.disabled = true;
    commitBtn.title = "Cannot commit read-only sections";
  } else {
    commitBtn.disabled = false;
    commitBtn.title = "Create git commit for current changes";
  }
}
