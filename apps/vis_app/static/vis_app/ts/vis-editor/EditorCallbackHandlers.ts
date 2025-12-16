/**
 * EditorCallbackHandlers - Extracted callback handlers from VisEditor
 *
 * This class contains large callback handlers that were previously inline
 * in VisEditor.initializeEditor(), improving readability and maintainability.
 */

import type { CanvasManager } from '../vis/CanvasManager';
import type { PropertiesManager } from '../vis/PropertiesManager';
import type { DataTableManager } from '../vis/ui/DataTabManager';
import type { RulersManager } from '../vis/RulersManager';

interface HandlerDependencies {
    canvasManager: CanvasManager;
    propertiesManager: PropertiesManager;
    dataTableManager: DataTableManager;
    rulersManager: RulersManager;
    syncTreeToPanel: (pltzPath: string) => void;
    loadCsvDataInTab: (obj: any) => void;
    loadCsvForBundlePanel: (obj: any) => Promise<void>;
    loadCsvForImage: (obj: any) => Promise<void>;
    updateStatusBar: (message: string) => void;
    inferCsvColumnsFromLabel: (elementName: string, elementInfo: any) => any;
    updateRulersAreaTransform: () => void;
}

export class EditorCallbackHandlers {
    private deps: HandlerDependencies;

    constructor(dependencies: HandlerDependencies) {
        this.deps = dependencies;
    }

    /**
     * Handle canvas object selection
     * Extracted from initializeEditor line 340-362 (23 lines)
     */
    public createSelectionCallback() {
        return async (obj: any) => {
            if (obj) {
                this.deps.propertiesManager.showCanvasObjectProperties(obj);

                // Sync tree to highlight selected panel's file
                if (obj.isBundlePanel && obj.pltzPath) {
                    this.deps.syncTreeToPanel(obj.pltzPath);
                }

                // Handle CSV data in dedicated tab
                if (obj.csvData) {
                    this.deps.loadCsvDataInTab(obj);
                } else if (obj.isBundlePanel && obj.pltzPath) {
                    // Load CSV from bundle for panel selection
                    await this.deps.loadCsvForBundlePanel(obj);
                } else if (obj.name) {
                    // Try to fetch CSV data from gallery based on object name
                    await this.deps.loadCsvForImage(obj);
                }
            } else {
                this.deps.propertiesManager.showNoSelection();
            }
        };
    }

    /**
     * Handle element selection with CSV column highlighting
     * Extracted from initializeEditor line 370-438 (69 lines)
     */
    public createElementSelectionCallback() {
        return (elementNames: string[], elementInfos: any[]) => {
            if (elementNames.length > 0 && elementInfos.length > 0) {
                // Use first selected element for properties panel
                const elementName = elementNames[0];
                const elementInfo = elementInfos[0];

                console.log(`[VisEditor] Elements selected: ${elementNames.join(', ')}`, elementInfos);

                // Show element properties in right panel
                this.deps.propertiesManager.showElementProperties(elementName, elementInfo);

                // Collect all column indices from all selected elements
                const allColumnIndices: Set<number> = new Set();
                const allColumnNames: string[] = [];

                for (let i = 0; i < elementNames.length; i++) {
                    const info = elementInfos[i];
                    if (!info) continue;

                    // Get csv_columns from elementInfo, or try to infer from canvas object's csvData
                    let csvCols = info.csv_columns;

                    // If csv_columns is not available (old figures), try to infer from csvData
                    const inferrableTypes = ['line', 'scatter', 'bar', 'boxplot', 'violin'];
                    if (!csvCols && info.element_type && inferrableTypes.includes(info.element_type)) {
                        csvCols = this.deps.inferCsvColumnsFromLabel(elementNames[i], info);
                    }

                    if (csvCols) {
                        if (csvCols.x?.index !== undefined) {
                            allColumnIndices.add(csvCols.x.index);
                            if (csvCols.x.name) allColumnNames.push(csvCols.x.name);
                        }
                        if (csvCols.y?.index !== undefined) {
                            allColumnIndices.add(csvCols.y.index);
                            if (csvCols.y.name) allColumnNames.push(csvCols.y.name);
                        }
                    }
                }

                // Highlight CSV columns if available
                const columnIndices = Array.from(allColumnIndices);
                if (columnIndices.length > 0) {
                    console.log(`[VisEditor] Highlighting columns: ${columnIndices.join(', ')}`);
                    this.deps.dataTableManager.highlightColumns(columnIndices);

                    // Update status bar with column info
                    const uniqueNames = [...new Set(allColumnNames)];
                    const colNamesStr = uniqueNames.join(', ');
                    if (elementNames.length === 1) {
                        this.deps.updateStatusBar(`Element: ${elementInfo.label || elementName} (columns: ${colNamesStr})`);
                    } else {
                        this.deps.updateStatusBar(`${elementNames.length} elements selected (columns: ${colNamesStr})`);
                    }
                } else {
                    console.log(`[VisEditor] No csv_columns on selected elements`);
                    if (elementNames.length === 1) {
                        this.deps.updateStatusBar(`Element: ${elementInfo.label || elementName}`);
                    } else {
                        this.deps.updateStatusBar(`${elementNames.length} elements selected`);
                    }
                }
            } else {
                // Clear highlights when no element selected
                this.deps.dataTableManager.clearColumnHighlights();
            }
        };
    }

    /**
     * Handle ruler transform updates
     * Extracted from initializeEditor line 444-450 (7 lines)
     */
    public createTransformCallback() {
        return () => {
            // Sync pan offset from RulersManager to CanvasManager
            const rulerPan = this.deps.rulersManager.getCanvasPanOffset();
            this.deps.canvasManager.setCanvasPanOffset(rulerPan.x, rulerPan.y);
            // Update the transform using CanvasManager's values
            this.deps.updateRulersAreaTransform();
        };
    }

    /**
     * Handle canvas restoration after initialization
     * Extracted from initializeEditor line 472-508 (37 lines)
     */
    public createCanvasRestorationCallback(
        canvasTabManager: any,
        restoreCanvasForTab: (tabId: string) => Promise<void>,
        loadMissingMetadata: (objects: any[]) => Promise<void>,
        saveCanvasForCurrentTab: () => void
    ) {
        return async () => {
            const activeTab = canvasTabManager.getActiveTab();
            if (activeTab?.canvasJson) {
                // Restore from canvas tab state
                await restoreCanvasForTab(activeTab.id);
                console.log(`[VisEditor] Restored canvas from tab: ${activeTab.figureName}`);
            } else {
                // Fallback: Try to restore from old single-canvas localStorage
                const savedState = localStorage.getItem('scitex-vis-viewstate');
                if (savedState) {
                    const restoredObjects = await this.deps.canvasManager.restoreCanvasContent();
                    await loadMissingMetadata(restoredObjects);
                    this.deps.updateRulersAreaTransform();
                    console.log(`[VisEditor] Restored view: ${Math.round(this.deps.canvasManager.getCanvasZoomLevel() * 100)}%`);

                    // Migrate: Save this to the default tab
                    saveCanvasForCurrentTab();
                } else {
                    // First time - zoom to fit
                    this.deps.canvasManager.zoomToFit();
                    this.deps.updateRulersAreaTransform();
                    console.log(`[VisEditor] Initial zoom: ${Math.round(this.deps.canvasManager.getCanvasZoomLevel() * 100)}%`);
                }
            }

            // Re-apply canvas theme AFTER content restoration
            const savedGlobalTheme = localStorage.getItem('scitex-theme-preference') || 'dark';
            const savedCanvasTheme = localStorage.getItem('canvas-theme') || savedGlobalTheme;
            const canvasDarkMode = savedCanvasTheme === 'dark';
            this.deps.canvasManager.updateCanvasTheme(canvasDarkMode);
            console.log(`[VisEditor] Canvas theme re-applied after restore: ${savedCanvasTheme}`);

            // Redraw rulers after canvas is fully loaded
            this.deps.rulersManager.drawRulers();
            console.log(`[VisEditor] Rulers redrawn after canvas restore`);
        };
    }
}
