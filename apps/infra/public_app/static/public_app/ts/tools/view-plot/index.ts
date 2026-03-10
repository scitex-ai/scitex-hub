// Plot Viewer - Barrel Export

import { PlotViewer } from "./_PlotViewer";

export { PlotViewer } from "./_PlotViewer";
export { PlotRenderer } from "./_renderers";
export { ControlsManager } from "./_controls";
export { ExportManager } from "./_export";
export { parseCSV, detectPlots, getDemoData } from "./_data";
export { generateNiceTicks, formatNumber, updateInfoPanel } from "./_utils";
export { drawLine, drawScatter, drawBar } from "./_plot-drawers";
export type {
  PlotSettings,
  PlotData,
  Plot,
  PlotArea,
  Scale,
  Margin,
} from "./types";
export { NATURE_COLORS, DEFAULT_SETTINGS } from "./types";

// Initialize global instance when DOM is ready
let plotViewerInstance: PlotViewer | null = null;

document.addEventListener("DOMContentLoaded", () => {
  plotViewerInstance = new PlotViewer("plotCanvas");

  // Expose global functions for backward compatibility
  (window as any).toggleSettingsPanel = () => {
    plotViewerInstance?.toggleSettings();
  };

  (window as any).updateSetting = (param: string, value: string | number) => {
    plotViewerInstance?.updateSetting(param, value);
  };

  (window as any).resetToNatureDefaults = () => {
    plotViewerInstance?.resetSettings();
  };

  (window as any).downloadPlot = () => {
    plotViewerInstance?.downloadPlot();
  };

  (window as any).loadDemoData = () => {
    plotViewerInstance?.loadDemoData();
  };
});
