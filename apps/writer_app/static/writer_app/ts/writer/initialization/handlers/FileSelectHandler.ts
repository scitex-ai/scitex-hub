/**
 * File Select Handler
 * Handles file/section selection from dropdown or tree
 */

import { switchSection } from "../../../utils/index.js";
import { loadTexFile } from "../../files/FileLoader.js";

console.log("[DEBUG] FileSelectHandler.ts loaded");

export interface FileSelectDependencies {
  config: any;
  editor: any;
  sectionsManager: any;
  state: any;
  pdfPreviewManager: any;
}

/**
 * Create the file/section select handler
 */
export function createFileSelectHandler(deps: FileSelectDependencies) {
  return async (sectionId: string, sectionName: string): Promise<void> => {
    console.log(
      "[FileSelectHandler] File/section selected:",
      sectionName,
      "ID:",
      sectionId,
    );

    // Check if this is a section ID pattern (doctype/section format) or a file path
    // Section IDs follow: {docType}/{sectionName} where doctype is manuscript|supplementary|revision
    // File paths have .tex extension or are in shared/* directories
    const sectionPattern = /^(manuscript|supplementary|revision)\/([a-z_]+)$/;
    const sectionMatch = sectionId.match(sectionPattern);

    if (sectionMatch) {
      await handleSectionId(sectionMatch, sectionId, deps);
    } else if (sectionId.endsWith(".tex")) {
      await handleTexFile(sectionId, deps);
    } else {
      handleFallback(sectionId, deps);
    }
  };
}

/**
 * Handle section ID selection (e.g., "manuscript/abstract")
 */
async function handleSectionId(
  sectionMatch: RegExpMatchArray,
  sectionId: string,
  deps: FileSelectDependencies
): Promise<void> {
  const docType = sectionMatch[1];
  const sectionNameParsed = sectionMatch[2];

  console.log(
    "[FileSelectHandler] Detected section ID, switching section:",
    sectionId,
    "docType:",
    docType,
    "section:",
    sectionNameParsed,
  );

  // Skip loading .tex file for compiled sections (they show PDF directly)
  const isCompiledSection =
    sectionNameParsed === "compiled_pdf" || sectionNameParsed === "compiled_tex";

  if (!isCompiledSection && deps.config.projectId) {
    // Get the expected .tex file path
    const { getWriterFilter } = await import("../../../modules/writer-file-filter.js");
    const filter = getWriterFilter();
    const texFilePath = filter.getExpectedFilePath(docType, sectionNameParsed);
    console.log("[FileSelectHandler] Loading .tex file for section:", texFilePath);

    // Load the .tex file content
    loadTexFile(texFilePath, deps.editor);

    // Expand file tree to show the corresponding file
    const filesTree = (window as any).writerFileTree;
    if (filesTree && filesTree.expandPath) {
      console.log("[FileSelectHandler] Expanding file tree to:", texFilePath);
      filesTree.expandPath(texFilePath);
    }
  }

  // Also switch section for state management
  switchSection(
    deps.editor,
    deps.sectionsManager,
    deps.state,
    sectionId,
    deps.pdfPreviewManager,
  );
}

/**
 * Handle direct .tex file selection
 */
async function handleTexFile(
  sectionId: string,
  deps: FileSelectDependencies
): Promise<void> {
  console.log("[FileSelectHandler] Detected .tex file, loading from disk:", sectionId);
  loadTexFile(sectionId, deps.editor);

  // Expand file tree to show the file
  const filesTree = (window as any).writerFileTree;
  if (filesTree && filesTree.expandPath) {
    console.log("[FileSelectHandler] Expanding file tree to:", sectionId);
    filesTree.expandPath(sectionId);
  }
}

/**
 * Handle fallback case (try as section)
 */
function handleFallback(sectionId: string, deps: FileSelectDependencies): void {
  console.log("[FileSelectHandler] Unknown ID format, trying as section:", sectionId);
  switchSection(
    deps.editor,
    deps.sectionsManager,
    deps.state,
    sectionId,
    deps.pdfPreviewManager,
  );
}
