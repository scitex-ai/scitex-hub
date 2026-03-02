/**
 * Tree Configuration
 * Writer-specific tree configuration and folder mapping
 */

console.log("[DEBUG] TreeConfiguration.ts loaded");

/**
 * Default allowed extensions for writer file tree
 */
export const WRITER_ALLOWED_EXTENSIONS = [
  '.tex', '.bib', '.cls', '.sty', '.pdf',
  '.csv', '.xlsx', '.xls',
  '.png', '.jpg', '.jpeg', '.svg', '.eps',
  '.bbl', '.bst'
];

/**
 * Doctype to folder path mapping
 */
export const DOCTYPE_FOLDER_MAP: Record<string, string> = {
  'manuscript': 'scitex/writer/01_manuscript',
  'supplementary': 'scitex/writer/02_supplementary',
  'revision': 'scitex/writer/03_revision',
  'shared': 'scitex/writer/00_shared',
};

/**
 * Get folder path for a doctype
 * @param doctype - manuscript, supplementary, revision, or shared
 * @returns Folder path like 'scitex/writer/01_manuscript'
 */
export function getDoctypeFolder(doctype: string): string {
  return DOCTYPE_FOLDER_MAP[doctype] || 'scitex/writer/01_manuscript';
}

/**
 * Create tree configuration for writer
 */
export function createWriterTreeConfig(
  projectOwner: string,
  projectSlug: string,
  onFileSelect: (path: string, item: any) => void
): any {
  return {
    mode: 'writer',
    containerId: 'writer-file-tree',
    username: projectOwner,
    slug: projectSlug,
    showFolderActions: true,
    showGitStatus: true,
    allowedExtensions: WRITER_ALLOWED_EXTENSIONS,
    onFileSelect,
  };
}
