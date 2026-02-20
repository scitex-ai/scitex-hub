/**
 * Workspace Panel Resizer — entry point re-export
 * Delegates to the workspace-panel-resizer/ directory implementation.
 */
export type { PanelConfig } from "./workspace-panel-resizer/index";
export {
  WorkspacePanelResizer,
  workspacePanelResizer,
  autoInitPanels,
} from "./workspace-panel-resizer/index";
