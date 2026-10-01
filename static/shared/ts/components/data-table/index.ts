/**
 * Re-export from scitex-ui — the canonical implementation.
 * scitex-hub consumers should import from "@/components/data-table".
 */

export { DataTableManager } from "@scitex/sdk/ui/ts/app/data-table/DataTableManager";
export { TableData } from "@scitex/sdk/ui/ts/app/data-table/_TableData";
export { TableRendering } from "@scitex/sdk/ui/ts/app/data-table/_TableRendering";
export { TableSelection } from "@scitex/sdk/ui/ts/app/data-table/_TableSelection";
export { TableEditing } from "@scitex/sdk/ui/ts/app/data-table/_TableEditing";
export { TableClipboard } from "@scitex/sdk/ui/ts/app/data-table/_TableClipboard";
export { TableFillHandle } from "@scitex/sdk/ui/ts/app/data-table/_TableFillHandle";
export { TableColumnRow } from "@scitex/sdk/ui/ts/app/data-table/_TableColumnRow";

export type {
  Dataset,
  DataRow,
  CellPosition,
  SelectionState,
  DataTableConfig,
} from "@scitex/sdk/ui/ts/app/data-table/types";

export { TABLE_CONSTANTS } from "@scitex/sdk/ui/ts/app/data-table/types";
