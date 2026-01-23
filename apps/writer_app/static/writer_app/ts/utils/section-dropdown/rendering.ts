/**
 * Dropdown Rendering
 * Generates HTML for section dropdown items
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/section-dropdown/rendering.ts loaded",
);

/**
 * Generate file path for a section
 *
 * @param section - Section object
 * @param docType - Document type
 * @returns File path URL
 */
function generateFilePath(section: any, docType: string): string {
  const username =
    (window as any).WRITER_CONFIG?.projectOwner || "ywatanabe";
  const projectSlug =
    (window as any).WRITER_CONFIG?.projectSlug || "default-project";

  // Use the path from backend if available, otherwise construct default path
  if (section.path) {
    // Backend provides the correct path like "01_manuscript/contents/abstract.tex"
    return `/${username}/${projectSlug}/blob/scitex/writer/${section.path}`;
  } else {
    // Fallback for sections without explicit path
    const sectionPath = section.id.replace(`${docType}/`, "");
    const docDirMap: Record<string, string> = {
      manuscript: "01_manuscript",
      supplementary: "02_supplementary",
      revision: "03_revision",
    };
    const docDir = docDirMap[docType] || `01_${docType}`;
    return `/${username}/${projectSlug}/blob/scitex/writer/${docDir}/contents/${sectionPath}.tex`;
  }
}

/**
 * Generate HTML for a single section item
 *
 * @param section - Section object
 * @param index - Section index
 * @param docType - Document type
 * @returns HTML string for the section item
 */
function renderSectionItem(
  section: any,
  index: number,
  docType: string,
): string {
  const isExcluded = section.excluded === true;
  const isOptional = section.optional === true;
  const isViewOnly = section.view_only === true;
  const isCompiledPdf = section.name === "compiled_pdf";
  const sectionLabel = section.label;

  // Don't show toggle for view-only sections (like compiled_pdf)
  const showToggle = !isViewOnly && (isOptional || isExcluded);

  const filePath = generateFilePath(section, docType);

  return `
        <div class="section-item ${isExcluded ? "excluded" : ""} section-item-with-actions"
             data-section-id="${section.id}"
             data-index="${index}"
             data-optional="${isOptional}"
             draggable="${!isCompiledPdf}"
             title="${isCompiledPdf ? "View " + sectionLabel : "Switch to " + sectionLabel}">
            <span class="section-drag-handle" style="${isCompiledPdf ? "visibility: hidden;" : ""}" title="Drag to reorder">⋮⋮</span>
            ${!isCompiledPdf ? `<span class="section-page-number" style="color: var(--color-fg-muted); font-size: 0.75rem; min-width: 20px;">${index + 1}</span>` : ""}
            <span class="section-item-name">${sectionLabel}</span>
            ${
              showToggle
                ? `
                <label class="ios-toggle" data-action="toggle-visibility" title="${isExcluded ? "Include in compilation" : "Exclude from compilation"}">
                    <input type="checkbox" ${!isExcluded ? "checked" : ""}>
                    <span class="ios-toggle-slider"></span>
                </label>
            `
                : ""
            }
            <div class="section-item-actions">
                ${
                  isCompiledPdf
                    ? `
                    <button class="btn btn-xs btn-outline-secondary" data-action="compile-full" title="Compile ${sectionLabel} PDF" onclick="event.stopPropagation();">
                        <i class="fas fa-file-pdf"></i>
                    </button>
                `
                    : ""
                }
                <a href="${filePath}" class="btn btn-xs btn-outline-secondary" title="Go to ${sectionLabel} file" onclick="event.stopPropagation();" target="_blank">
                    <i class="fas fa-folder-open"></i>
                </a>
                <button class="btn btn-xs btn-outline-secondary" data-action="download-section" title="Download ${sectionLabel} PDF" onclick="event.stopPropagation();">
                    <i class="fas fa-download"></i>
                </button>
            </div>
        </div>
    `;
}

/**
 * Render the complete section dropdown HTML
 *
 * @param sections - Array of section objects
 * @param docType - Document type
 * @returns Complete dropdown HTML
 */
export function renderSectionDropdown(
  sections: any[],
  docType: string,
): string {
  // Separate regular sections from footer items (compiled PDFs, New Section)
  let regularSectionsHtml = "";
  let footerSectionsHtml = "";

  sections.forEach((section: any, index: number) => {
    const isCompiledPdf = section.name === "compiled_pdf";
    const itemHtml = renderSectionItem(section, index, docType);

    // Separate compiled sections to footer
    if (isCompiledPdf) {
      footerSectionsHtml += itemHtml;
    } else {
      regularSectionsHtml += itemHtml;
    }
  });

  // Build final HTML with scrollable sections + fixed footer
  return `
        <div class="section-items-scrollable">
            ${regularSectionsHtml}
        </div>
        <div class="section-items-footer">
            <div class="section-divider"></div>
            ${footerSectionsHtml}
            <div class="section-divider"></div>
            <div class="section-action-item" data-action="new-section">
                <i class="fas fa-plus"></i>
                <span>Add New Section</span>
            </div>
        </div>
    `;
}
