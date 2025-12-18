/**
 * Data table linking operations for canvas tabs
 * Links are stored in memory only (tabs are derived from filesystem)
 */

import type { CanvasTab } from "./CanvasTabTypes";

export function getLinkedDataTableIds(
  tabs: CanvasTab[],
  figureId: string,
): string[] {
  return tabs.find((t) => t.id === figureId)?.linkedDataTableIds || [];
}

export function linkDataTable(
  tabs: CanvasTab[],
  figureId: string,
  dataTableId: string,
): void {
  const tab = tabs.find((t) => t.id === figureId);
  if (tab) {
    tab.linkedDataTableIds = tab.linkedDataTableIds || [];
    if (!tab.linkedDataTableIds.includes(dataTableId)) {
      tab.linkedDataTableIds.push(dataTableId);
    }
  }
}

export function unlinkDataTable(
  tabs: CanvasTab[],
  figureId: string,
  dataTableId: string,
): void {
  const tab = tabs.find((t) => t.id === figureId);
  if (tab?.linkedDataTableIds) {
    tab.linkedDataTableIds = tab.linkedDataTableIds.filter(
      (id) => id !== dataTableId,
    );
  }
}
