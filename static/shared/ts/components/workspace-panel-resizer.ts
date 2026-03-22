/**
 * Workspace Panel Resizer — re-exports from scitex-ui (single source of truth).
 * Do NOT duplicate resizer logic in scitex-cloud.
 */
export type { PanelConfig } from "scitex-ui/ts/shell/workspace-panel-resizer/index";
export type { AxisConfig } from "scitex-ui/ts/shell/workspace-panel-resizer/index";
export {
  WorkspacePanelResizer,
  workspacePanelResizer,
  autoInitPanels,
  initNewPanels,
  detectAxis,
  getAxis,
} from "scitex-ui/ts/shell/workspace-panel-resizer/index";
