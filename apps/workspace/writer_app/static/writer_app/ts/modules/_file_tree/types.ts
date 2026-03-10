/**
 * File Tree Type Definitions
 */

export interface FileTreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileTreeNode[];
}

export interface FileTreeOptions {
  projectId: number;
  container: HTMLElement;
  onFileSelect?: (filePath: string, fileName: string) => void;
  texFileDropdownId?: string;
}

export interface TeXSection {
  title: string;
  filePath: string;
}
