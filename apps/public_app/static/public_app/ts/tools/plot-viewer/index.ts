// Plot Viewer - Barrel Export

import { PlotViewer } from './PlotViewer.ts';

export { PlotViewer } from './PlotViewer.ts';
export { PlotRenderer } from './renderers.ts';
export { ControlsManager } from './controls.ts';
export { ExportManager } from './export.ts';
export { parseCSV, detectPlots, getDemoData } from './data.ts';
export { generateNiceTicks, formatNumber, updateInfoPanel } from './utils.ts';
export { drawLine, drawScatter, drawBar } from './plot-drawers.ts';
export type { PlotSettings, PlotData, Plot, PlotArea, Scale, Margin } from './types.ts';
export { NATURE_COLORS, DEFAULT_SETTINGS } from './types.ts';

// Initialize global instance when DOM is ready
let plotViewerInstance: PlotViewer | null = null;

document.addEventListener('DOMContentLoaded', () => {
    plotViewerInstance = new PlotViewer('plotCanvas');

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
