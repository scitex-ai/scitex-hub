/**
 * Type definitions for table preview modal
 */

console.log("[DEBUG] table-preview-modal/types.ts loaded");

export interface TableData {
  data: Record<string, any>[];
  columns: string[];
  metadata: {
    file_name: string;
    file_path: string;
    file_type: string;
    file_hash: string;
    rows: number;
    cols: number;
  };
}

export interface TableState {
  projectId: string | null;
  currentTable: TableData | null;
  currentFileHash: string | null;
  selectedRows: Set<number>;
  modifiedCells: Map<string, any>;
  renamedColumns: Map<string, string>;
  deletedColumns: Set<string>;
  isModified: boolean;
}
