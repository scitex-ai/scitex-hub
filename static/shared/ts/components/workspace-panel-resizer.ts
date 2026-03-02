/**
 * Workspace Panel Resizer — entry point re-export
 * Delegates to the workspace-panel-resizer/ directory implementation.
 */
export type { PanelConfig } from "./_workspace-panel-resizer/index";
export {
  WorkspacePanelResizer,
  workspacePanelResizer,
  autoInitPanels,
  initNewPanels,
} from "./_workspace-panel-resizer/index";
