/**
 * Workspace Panel Resizer — re-exports from scitex-ui (single source of truth).
 * Do NOT duplicate resizer logic in scitex-hub.
 */
export type { PanelConfig } from "@scitex/sdk/ui/ts/shell/workspace-panel-resizer/index";
export type { AxisConfig } from "@scitex/sdk/ui/ts/shell/workspace-panel-resizer/index";
export {
  WorkspacePanelResizer,
  workspacePanelResizer,
  autoInitPanels,
  initNewPanels,
  detectAxis,
  getAxis,
} from "@scitex/sdk/ui/ts/shell/workspace-panel-resizer/index";
