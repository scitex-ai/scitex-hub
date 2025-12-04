/**
 * File Tree Integration Module
 * Handles integration between WorkspaceFilesTree and writer components
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/writer/tree/file-tree-integration.ts loaded"
);

import {
  doctypeToDirectory,
  doctypeDirs,
  systemDirs,
  isNonEditableFile,
  getDoctypeFromPath,
} from "../config/index.js";
import { getSectionsForDoctype, Section } from "../sections/section-extraction.js";

// State
let currentDoctype = "manuscript";
let currentSectionIndex = 0;

/**
 * Get current doctype
 */
export const getCurrentDoctype = (): string => currentDoctype;

/**
 * Set current doctype
 */
export const setCurrentDoctype = (doctype: string): void => {
  currentDoctype = doctype;
  console.log("[Writer] Doctype changed to:", doctype);
};

/**
 * Get current section index
 */
export const getCurrentSectionIndex = (): number => currentSectionIndex;

/**
 * Set current section index
 */
export const setCurrentSectionIndex = (index: number): void => {
  currentSectionIndex = index;
};

/**
 * Filter the file tree DOM to show only the current doctype's directory
 */
export const filterFileTreeDOM = (doctype: string): void => {
  const dirPath = doctypeToDirectory[doctype];
  if (!dirPath) return;

  const treeContainer = document.getElementById("writer-file-tree");
  if (!treeContainer) return;

  const targetDirName = dirPath.split("/").pop();
  const allItems = treeContainer.querySelectorAll(".wft-item");

  allItems.forEach((item) => {
    const path = item.getAttribute("data-path") || "";
    const pathParts = path.split("/");
    const folderName = pathParts[pathParts.length - 1];

    // Check if this is a top-level doctype or system folder
    const isTopLevelDoctypeDir = doctypeDirs.includes(folderName);
    const isSystemDir = systemDirs.includes(folderName);

    if (isTopLevelDoctypeDir) {
      const element = item as HTMLElement;
      const childrenContainer = item.nextElementSibling as HTMLElement | null;
      const shouldShow = folderName === targetDirName;

      element.style.display = shouldShow ? "" : "none";
      if (childrenContainer?.classList?.contains("wft-children")) {
        childrenContainer.style.display = shouldShow ? "" : "none";
      }
    } else if (isSystemDir) {
      // Hide system directories
      const element = item as HTMLElement;
      const childrenContainer = item.nextElementSibling as HTMLElement | null;
      element.style.display = "none";
      if (childrenContainer?.classList?.contains("wft-children")) {
        childrenContainer.style.display = "none";
      }
    }
  });

  console.log("[Writer] File tree filtered to show only:", doctype);
};

/**
 * Synchronize all components (doctype dropdown, section dropdown, tree) from a file path
 */
export const syncAllFromPath = (
  path: string,
  callbacks: {
    onDoctypeChange?: (doctype: string) => void;
    onSectionChange?: (section: Section, index: number) => void;
    onTreeSelect?: (path: string) => void;
  }
): void => {
  // Detect doctype from path
  let detectedDoctype = getDoctypeFromPath(path);

  if (detectedDoctype && detectedDoctype !== currentDoctype) {
    currentDoctype = detectedDoctype;
    callbacks.onDoctypeChange?.(detectedDoctype);
    filterFileTreeDOM(detectedDoctype);
  }

  // Find matching section
  const sections = getSectionsForDoctype(currentDoctype);
  const fileName = path.split("/").pop();
  let foundSection = false;

  for (let i = 0; i < sections.length; i++) {
    if (sections[i].path === path || sections[i].file.endsWith(fileName || "")) {
      currentSectionIndex = i;
      foundSection = true;
      callbacks.onSectionChange?.(sections[i], i);
      break;
    }
  }

  // Select in tree if needed
  if (callbacks.onTreeSelect) {
    callbacks.onTreeSelect(path);
  }
};

/**
 * Handle doctype change from dropdown
 */
export const handleDoctypeChange = (
  doctype: string,
  callbacks: {
    onUpdateSectionOptions?: (doctype: string) => void;
    onSelectDefaultSection?: () => void;
  }
): void => {
  currentDoctype = doctype;
  currentSectionIndex = 0;
  filterFileTreeDOM(doctype);
  callbacks.onUpdateSectionOptions?.(doctype);
  callbacks.onSelectDefaultSection?.();
};

/**
 * Determine file type and dispatch appropriate event
 */
export const handleFileSelect = (
  path: string,
  callbacks: {
    onLoadFile?: (path: string, readOnly: boolean) => void;
    onShowPdf?: (path: string) => void;
    onShowFigure?: (path: string) => void;
    onShowTable?: (path: string) => void;
    onShowData?: (path: string) => void;
  }
): void => {
  const fileName = path.split("/").pop()?.toLowerCase() || "";
  const extension = fileName.split(".").pop() || "";
  const readOnly = isNonEditableFile(path);

  // PDF files
  if (extension === "pdf") {
    callbacks.onShowPdf?.(path);
    return;
  }

  // Image files
  if (["png", "jpg", "jpeg", "gif", "svg", "webp"].includes(extension)) {
    callbacks.onShowFigure?.(path);
    return;
  }

  // Table/data files
  if (["csv", "xlsx", "xls", "tsv"].includes(extension)) {
    callbacks.onShowTable?.(path);
    return;
  }

  // BibTeX files
  if (["bib", "bbl", "bst"].includes(extension)) {
    callbacks.onShowData?.(path);
    return;
  }

  // Text/TeX files - load into editor
  callbacks.onLoadFile?.(path, readOnly);
};

/**
 * Setup mutation observer to auto-filter tree when it updates
 */
export const setupTreeFilterObserver = (filterDebounceMs: number = 100): void => {
  const treeContainer = document.getElementById("writer-file-tree");
  if (!treeContainer) return;

  let filterDebounce: ReturnType<typeof setTimeout>;

  const observer = new MutationObserver(() => {
    clearTimeout(filterDebounce);
    filterDebounce = setTimeout(() => {
      filterFileTreeDOM(currentDoctype);
    }, filterDebounceMs);
  });

  observer.observe(treeContainer, {
    childList: true,
    subtree: true,
  });
};
