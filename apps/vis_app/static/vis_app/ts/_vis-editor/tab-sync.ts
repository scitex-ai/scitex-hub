/**
 * Tab Synchronization Helper
 * Handles synchronization between canvas tabs and data tabs
 */

import type { CanvasTabManager } from "../_vis/ui/CanvasTabManager";
import type { DataTabManager } from "../_vis/ui/DataTabManager";

/**
 * Sync data tab when canvas tab changes
 * Switches to the first linked data table for the active figure
 */
export function syncDataTabToCanvasTab(
  canvasTabManager: CanvasTabManager,
  dataTabManager: DataTabManager,
): void {
  const activeTab = canvasTabManager.getActiveTab();
  if (!activeTab) return;

  const linkedDataIds = activeTab.linkedDataTableIds || [];
  if (linkedDataIds.length > 0) {
    const firstLinkedId = linkedDataIds[0];
    // Check if the tab exists before switching
    const existingTab = dataTabManager.getTab(firstLinkedId);
    if (existingTab) {
      dataTabManager.switchToTab(firstLinkedId);
      console.log(`[TabSync] Synced data tab to: ${firstLinkedId}`);
    } else {
      console.log(`[TabSync] Linked data tab not found: ${firstLinkedId}`);
    }
  }
}

/**
 * Link a data tab to the current canvas tab
 */
export function linkDataTabToCanvasTab(
  canvasTabManager: CanvasTabManager,
  dataTabId: string,
): void {
  const activeTab = canvasTabManager.getActiveTab();
  if (!activeTab) return;

  canvasTabManager.linkDataTable(activeTab.id, dataTabId);
  console.log(
    `[TabSync] Linked data tab ${dataTabId} to figure ${activeTab.id}`,
  );
}
