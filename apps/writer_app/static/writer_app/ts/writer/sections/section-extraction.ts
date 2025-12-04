/**
 * Section Extraction Module
 * Handles extracting sections from the file tree data
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/writer/sections/section-extraction.ts loaded"
);

import { doctypeToDirectory, skipFiles } from "../config/index.js";

export interface Section {
  id: string;
  label: string;
  file: string;
  path: string;
}

interface TreeItem {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: TreeItem[];
}

/**
 * Find a directory in the tree by path
 */
const findDir = (items: TreeItem[], targetPath: string): TreeItem | null => {
  for (const item of items) {
    if (item.path === targetPath) return item;
    if (item.children) {
      const found = findDir(item.children, targetPath);
      if (found) return found;
    }
  }
  return null;
};

/**
 * Convert filename to display label
 */
const fileNameToLabel = (fileName: string): string => {
  return fileName
    .replace(".tex", "")
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
};

/**
 * Extract sections from file tree data for a specific doctype
 */
export const extractSectionsFromTree = (
  treeData: TreeItem[],
  doctype: string
): Section[] => {
  const dirPath = doctypeToDirectory[doctype];
  if (!dirPath || !treeData) return [];

  const sections: Section[] = [];
  const doctypeDir = findDir(treeData, dirPath);
  if (!doctypeDir || !doctypeDir.children) return sections;

  if (doctype === "shared") {
    // For shared: get .tex files directly in 00_shared (not in subdirs)
    for (const item of doctypeDir.children) {
      if (
        item.type === "file" &&
        item.name.endsWith(".tex") &&
        !skipFiles.includes(item.name.toLowerCase())
      ) {
        sections.push({
          id: item.name.replace(".tex", ""),
          label: fileNameToLabel(item.name),
          file: item.name,
          path: item.path,
        });
      }
    }
  } else {
    // For manuscript/supplementary/revision: get .tex files in contents/
    const contentsDir = doctypeDir.children.find(
      (c) => c.name === "contents" && c.type === "directory"
    );

    if (contentsDir && contentsDir.children) {
      for (const item of contentsDir.children) {
        // Direct .tex files in contents/
        if (
          item.type === "file" &&
          item.name.endsWith(".tex") &&
          !skipFiles.includes(item.name.toLowerCase())
        ) {
          sections.push({
            id: item.name.replace(".tex", ""),
            label: fileNameToLabel(item.name),
            file: `contents/${item.name}`,
            path: item.path,
          });
        }
      }

      // Also check subdirectories in contents/ (like figures/, tables/)
      for (const subdir of contentsDir.children) {
        if (subdir.type === "directory" && subdir.children) {
          for (const item of subdir.children) {
            if (item.type === "file" && item.name.endsWith(".tex")) {
              sections.push({
                id: `${subdir.name}/${item.name.replace(".tex", "")}`,
                label: `${subdir.name}/${fileNameToLabel(item.name)}`,
                file: `contents/${subdir.name}/${item.name}`,
                path: item.path,
              });
            }
          }
        }
      }
    }
  }

  return sections;
};

/**
 * State for doctype sections - updated from tree data
 */
let doctypeSections: Record<string, Section[]> = {
  shared: [],
  manuscript: [],
  supplementary: [],
  revision: [],
};

/**
 * Update doctype sections from tree data
 */
export const updateDoctypeSectionsFromTree = (treeData: TreeItem[]): void => {
  for (const doctype of Object.keys(doctypeToDirectory)) {
    const sections = extractSectionsFromTree(treeData, doctype);
    if (sections.length > 0) {
      doctypeSections[doctype] = sections;
      console.log(
        `[Writer] Extracted ${sections.length} sections for ${doctype}:`,
        sections.map((s) => s.label)
      );
    }
  }
  console.log("[Writer] Sections populated from tree data");
};

/**
 * Get sections for a doctype
 */
export const getSectionsForDoctype = (doctype: string): Section[] => {
  return doctypeSections[doctype] || [];
};

/**
 * Set sections for a doctype (for external updates)
 */
export const setSectionsForDoctype = (
  doctype: string,
  sections: Section[]
): void => {
  doctypeSections[doctype] = sections;
};
