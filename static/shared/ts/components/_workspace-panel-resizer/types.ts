/** Panel configuration for WorkspacePanelResizer */
export interface PanelConfig {
  /** ID of the resizer element */
  resizerId: string;
  /** CSS selector for the panel to resize */
  targetPanel: string;
  /** Minimum width in pixels (collapsed state width) */
  minWidth: number;
  /** localStorage key for saved width */
  storageKey: string;
  /** Direction: 'left' = panel on left of resizer, 'right' = panel on right */
  resizeDirection: "left" | "right";
  /** Optional: ID of toggle button to sync icon state */
  toggleButtonId?: string;
  /** Optional: localStorage key for collapse state */
  collapseStorageKey?: string;
  /** Optional: Default width when not collapsed */
  defaultWidth?: number;
  /** Optional: Panel width is fixed — resizer only propagates to adjacent panels */
  fixedWidth?: boolean;
}
