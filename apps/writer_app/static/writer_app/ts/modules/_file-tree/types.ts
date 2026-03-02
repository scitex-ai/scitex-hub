/**
 * File Tree Types and Interfaces
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

export interface SectionConfig {
  id: string;
  label: string;
  optional?: boolean;
  view_only?: boolean;
}

export interface SectionsHierarchy {
  manuscript?: { sections: SectionConfig[] };
  supplementary?: { sections: SectionConfig[] };
  revision?: { sections: SectionConfig[] };
  shared?: { sections: SectionConfig[] };
}
