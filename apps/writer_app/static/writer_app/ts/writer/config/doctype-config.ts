/**
 * Doctype Configuration Module
 * Contains doctype-to-directory mappings and file handling configurations
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/writer/config/doctype-config.ts loaded"
);

// Mapping: doctype -> directory path
export const doctypeToDirectory: Record<string, string> = {
  shared: "scitex/writer/00_shared",
  manuscript: "scitex/writer/01_manuscript",
  supplementary: "scitex/writer/02_supplementary",
  revision: "scitex/writer/03_revision",
};

// Files to skip when building section list
export const skipFiles: string[] = [
  "wordcount.tex",
  "shared.tex",
  "base.tex",
  "main.tex",
];

// Directories to skip when looking for sections (non-content directories)
export const skipDirs: string[] = [
  "figures",
  "tables",
  "latex_styles",
  "archive",
  "output",
  "wordcounts",
  "logs",
];

// Non-editable files (view-only, no preview compilation)
export const nonEditableFiles: string[] = [
  // Full manuscripts
  "manuscript.tex",
  "supplementary.tex",
  "revision.tex",
  // Diff manuscripts
  "manuscript_diff.tex",
  "supplementary_diff.tex",
  "revision_diff.tex",
  // System files
  "base.tex",
  "wordcount.tex",
  "main.tex",
  "shared.tex",
];

// Doctype directory names for filtering
export const doctypeDirs: string[] = [
  "00_shared",
  "01_manuscript",
  "02_supplementary",
  "03_revision",
];

// System directories to hide in file tree
export const systemDirs: string[] = [
  "ai",
  "config",
  "docs",
  "requirements",
  "scripts",
  "tests",
  "texts",
];

/**
 * Check if a file is non-editable (read-only)
 */
export const isNonEditableFile = (path: string): boolean => {
  const fileName = path.split("/").pop();
  return fileName ? nonEditableFiles.includes(fileName) : false;
};

/**
 * Get directory path for a doctype
 */
export const getDoctypePath = (doctype: string): string | undefined => {
  return doctypeToDirectory[doctype];
};

/**
 * Get doctype from a file path
 */
export const getDoctypeFromPath = (path: string): string | null => {
  for (const [doctype, dirPath] of Object.entries(doctypeToDirectory)) {
    if (path.startsWith(dirPath)) {
      return doctype;
    }
  }
  return null;
};
