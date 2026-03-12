/**
 * CsvDataCoordinator - Handles CSV data loading and synchronization
 *
 * Extracted from VisEditor to maintain single responsibility.
 * Manages CSV data loading for gallery images, bundle panels, and data tabs.
 */

import type { DataTabManager } from '../../_vis/ui/DataTabManager';
import type { DataTableManager } from '../../_vis/DataTableManager';
import type { PropertiesManager } from '../../_vis/PropertiesManager';
import type { CanvasManager } from '../../_vis/CanvasManager';
import type { GalleryCategories } from '../../_vis/GalleryCategories';

export interface CsvDataCoordinatorDeps {
    dataTabManager: DataTabManager;
    dataTableManager: DataTableManager;
    propertiesManager: PropertiesManager;
    canvasManager: CanvasManager;
    galleryCategories: () => GalleryCategories | null;
    updateStatusBar: (message: string) => void;
    getTabTypeFromCategory: (category: string) => string;
}

export class CsvDataCoordinator {
    private deps: CsvDataCoordinatorDeps;

    // Tab-Figure synchronization maps
    private tabToFigureMap: Map<string, string> = new Map();
    private figureToTabMap: Map<string, string> = new Map();

    constructor(deps: CsvDataCoordinatorDeps) {
        this.deps = deps;
    }

    /**
     * Get the tab-to-figure mapping
     */
    public getTabToFigureMap(): Map<string, string> {
        return this.tabToFigureMap;
    }

    /**
     * Get the figure-to-tab mapping
     */
    public getFigureToTabMap(): Map<string, string> {
        return this.figureToTabMap;
    }

    /**
     * Parse CSV text to 2D array
     */
    public parseCSV(csvText: string): string[][] {
        const lines = csvText.trim().split('\n');
        return lines.map(line => {
            const values: string[] = [];
            let current = '';
            let inQuotes = false;

            for (const char of line) {
                if (char === '"') {
                    inQuotes = !inQuotes;
                } else if (char === ',' && !inQuotes) {
                    values.push(current.trim());
                    current = '';
                } else {
                    current += char;
                }
            }
            values.push(current.trim());
            return values;
        });
    }

    /**
     * Load CSV data into a dedicated tab for the figure
     */
    public loadCsvDataInTab(obj: any): void {
        const name = obj.name || 'Figure';
        const objId = obj.id || `obj_${Date.now()}`;

        // Ensure object has an ID
        if (!obj.id) {
            obj.id = objId;
        }

        // Check if tab already exists for this figure
        const existingTabId = this.figureToTabMap.get(objId);
        if (existingTabId) {
            // Switch to existing tab
            this.deps.dataTabManager.switchToTab(existingTabId);
            this.deps.dataTableManager.loadFromArray(obj.csvData, true);
            return;
        }

        // Create new tab for this figure
        const category = obj.plotInfo?.category || 'default';
        const tabType = this.deps.getTabTypeFromCategory(category);
        const tabId = this.deps.dataTabManager.createAndSwitchToTab(
            name,
            tabType as any,
            category.charAt(0).toUpperCase() + category.slice(1),
            name,
            obj.csvData
        );

        // Store the mapping
        this.tabToFigureMap.set(tabId, objId);
        this.figureToTabMap.set(objId, tabId);

        // Load CSV into data table
        this.deps.dataTableManager.loadFromArray(obj.csvData, true);
        this.deps.updateStatusBar(`Data tab created for ${name}`);
    }

    /**
     * Load CSV data and metadata for an image from the gallery
     */
    public async loadCsvForImage(obj: any): Promise<void> {
        const name = obj.name || '';
        if (!name) {
            console.log('[CsvDataCoordinator] No name on selected image, cannot load CSV');
            return;
        }

        console.log(`[CsvDataCoordinator] Looking up CSV for image: "${name}"`);

        try {
            // Try to find the plot in loaded gallery contents
            const galleryCategories = this.deps.galleryCategories();
            const contents = galleryCategories?.getContents();
            if (!contents) {
                console.log('[CsvDataCoordinator] Gallery contents not loaded yet');
                return;
            }

            console.log(`[CsvDataCoordinator] Searching ${Object.keys(contents.categories || {}).length} categories`);

            // Search for the plot by display name across all categories
            const nameLower = name.toLowerCase();
            let found = false;

            for (const [category, info] of Object.entries(contents.categories || {})) {
                const categoryInfo = info as any;
                const plot = categoryInfo.plots?.find((p: any) => {
                    const displayLower = (p.display_name || '').toLowerCase();
                    const plotNameLower = (p.name || '').toLowerCase();
                    return (
                        p.display_name === name ||
                        p.name === name ||
                        displayLower === nameLower ||
                        plotNameLower === nameLower ||
                        displayLower.includes(nameLower) ||
                        nameLower.includes(displayLower.replace('ax.', '').replace('stx_', ''))
                    );
                });

                if (plot) {
                    found = true;
                    console.log(`[CsvDataCoordinator] Found matching plot: ${plot.name} in ${category}`);
                    // Load CSV data
                    const csvUrl = plot.csv || `/apps/vis/api/gallery/project/${category}/${plot.name}/csv/`;
                    try {
                        const csvResponse = await fetch(csvUrl);
                        if (csvResponse.ok) {
                            const csvText = await csvResponse.text();
                            const csvData = this.parseCSV(csvText);
                            obj.csvData = csvData;
                            obj.plotInfo = { plot, category };
                            // Load into dedicated tab
                            this.loadCsvDataInTab(obj);
                        }
                    } catch (e) {
                        console.log(`[CsvDataCoordinator] No CSV found for ${name}`);
                    }

                    // Load axis metadata if not already present
                    if (!obj.axisMetadata) {
                        try {
                            const metaResponse = await fetch(`/apps/vis/api/gallery/metadata/${category}/${plot.name}/`);
                            if (metaResponse.ok) {
                                const metadata = await metaResponse.json();
                                if (metadata.success && metadata.axes_bbox_px) {
                                    obj.axisMetadata = {
                                        axes_bbox_px: metadata.axes_bbox_px,
                                        figure_size_px: metadata.figure_size_px,
                                        element_bboxes: metadata.element_bboxes,
                                        hitmap: metadata.hitmap,
                                        hitmap_color_map: metadata.hitmap_color_map
                                    };
                                    // Refresh properties panel to show metadata
                                    this.deps.propertiesManager.showCanvasObjectProperties(obj);
                                }
                            }
                        } catch (e) {
                            console.log(`[CsvDataCoordinator] No metadata found for ${name}`);
                        }
                    }
                    break;
                }
            }

            if (!found) {
                console.log(`[CsvDataCoordinator] No matching plot found for "${name}"`);
            }
        } catch (error) {
            console.error('[CsvDataCoordinator] Failed to load CSV for image:', error);
        }
    }

    /**
     * Load CSV data for a bundle panel and sync with data table
     */
    public async loadCsvForBundlePanel(obj: any): Promise<void> {
        const pltzPath = obj.pltzPath;
        const panelLabel = obj.panelLabel || 'Panel';

        if (!pltzPath) {
            console.log('[CsvDataCoordinator] No pltzPath on bundle panel');
            return;
        }

        console.log(`[CsvDataCoordinator] Loading CSV for bundle panel: ${pltzPath}`);

        try {
            const csvUrl = `/apps/vis/api/bundles/pltz/data/?path=${encodeURIComponent(pltzPath)}`;
            const response = await fetch(csvUrl);

            if (response.ok) {
                const csvText = await response.text();
                const csvData = this.parseCSV(csvText);

                // Store CSV data on the object for later use
                obj.csvData = csvData;

                // Create or switch to tab for this panel
                const tabType = 'default';
                this.deps.dataTabManager.createAndSwitchToTab(
                    `Panel ${panelLabel}`,
                    tabType as any,
                    'Bundle',
                    panelLabel,
                    csvData
                );

                // Load into data table
                this.deps.dataTableManager.loadFromArray(csvData, true);

                this.deps.updateStatusBar(`Data loaded for Panel ${panelLabel} (${csvData.length} rows)`);
                console.log(`[CsvDataCoordinator] Loaded CSV for bundle panel ${panelLabel}: ${csvData.length} rows`);
            } else {
                console.log(`[CsvDataCoordinator] No CSV data found for bundle: ${pltzPath}`);
                this.deps.updateStatusBar(`No data available for Panel ${panelLabel}`);
            }
        } catch (error) {
            console.error('[CsvDataCoordinator] Failed to load CSV for bundle panel:', error);
        }
    }

    /**
     * Load missing axis metadata for restored objects
     */
    public async loadMissingMetadata(objects: any[]): Promise<void> {
        if (!objects.length) return;

        const objectsNeedingMetadata = objects.filter(
            obj => obj.type === 'image' && !obj.axisMetadata && obj.plotInfo
        );

        if (!objectsNeedingMetadata.length) {
            console.log('[CsvDataCoordinator] All objects have axis metadata');
            return;
        }

        console.log(`[CsvDataCoordinator] Loading metadata for ${objectsNeedingMetadata.length} objects`);

        for (const obj of objectsNeedingMetadata) {
            try {
                const { category, plot } = obj.plotInfo;
                if (!category || !plot?.name) continue;

                const metaResponse = await fetch(`/apps/vis/api/gallery/metadata/${category}/${plot.name}/`);
                if (metaResponse.ok) {
                    const metadata = await metaResponse.json();
                    if (metadata.success && metadata.axes_bbox_px) {
                        obj.axisMetadata = {
                            axes_bbox_px: metadata.axes_bbox_px,
                            figure_size_px: metadata.figure_size_px,
                            element_bboxes: metadata.element_bboxes,
                            hitmap: metadata.hitmap,
                            hitmap_color_map: metadata.hitmap_color_map
                        };
                        console.log(`[CsvDataCoordinator] Loaded metadata for ${obj.name || plot.name}`);
                    }
                }
            } catch (e) {
                console.log(`[CsvDataCoordinator] Failed to load metadata for ${obj.name || 'unknown'}`);
            }
        }

        // Save updated canvas with metadata
        this.deps.canvasManager.saveCanvasContent();
    }

    /**
     * Infer csv_columns from element label when csv_columns is not available
     */
    public inferCsvColumnsFromLabel(
        elementName: string,
        elementInfo: any
    ): { x?: { name: string; index: number }; y?: { name: string; index: number } } | null {
        const currentData = this.deps.dataTableManager.getCurrentData();
        if (!currentData || !currentData.headers || currentData.headers.length === 0) {
            console.log('[CsvDataCoordinator] No data table loaded for column inference');
            return null;
        }

        const headers = currentData.headers;
        const label = (elementInfo.label || '').toLowerCase();
        const traceIdx = elementInfo.trace_idx;

        // Find matching columns by trace-id pattern in SciTeX headers
        let xColIdx = -1;
        let yColIdx = -1;

        for (let i = 0; i < headers.length; i++) {
            const header = headers[i].toLowerCase();

            const traceIdMatch = header.match(/trace-id-([^_]+)/);
            if (traceIdMatch) {
                const traceId = traceIdMatch[1];

                const labelMatches =
                    traceId.includes(label) ||
                    label.includes(traceId.replace('-', '').replace('_', '')) ||
                    traceId.startsWith(label);

                if (labelMatches) {
                    if (header.endsWith('_variable-x') || header.includes('_x_') || header.endsWith('-x')) {
                        xColIdx = i;
                    } else if (header.endsWith('_variable-y') || header.includes('_y_') || header.endsWith('-y')) {
                        yColIdx = i;
                    }
                }
            }
        }

        if (xColIdx !== -1 || yColIdx !== -1) {
            const result: { x?: { name: string; index: number }; y?: { name: string; index: number } } = {};
            if (xColIdx !== -1) {
                result.x = { name: headers[xColIdx], index: xColIdx };
            }
            if (yColIdx !== -1) {
                result.y = { name: headers[yColIdx], index: yColIdx };
            }
            console.log(`[CsvDataCoordinator] Inferred csv_columns from SciTeX header: x=${result.x?.name}, y=${result.y?.name}`);
            return result;
        }

        // Fallback: Try to find Y column by trace_idx
        if (traceIdx !== undefined && traceIdx + 1 < headers.length) {
            const xCol = { name: headers[0], index: 0 };
            const yColIdx = traceIdx + 1;
            const yCol = { name: headers[yColIdx], index: yColIdx };
            console.log(`[CsvDataCoordinator] Inferred csv_columns from trace_idx ${traceIdx}: x=${xCol.name}, y=${yCol.name}`);
            return { x: xCol, y: yCol };
        }

        // Fallback: Try to match by label name
        for (let i = 1; i < headers.length; i++) {
            const header = headers[i].toLowerCase();
            if (label.includes(header) || header.includes(label)) {
                const xCol = { name: headers[0], index: 0 };
                const yCol = { name: headers[i], index: i };
                console.log(`[CsvDataCoordinator] Inferred csv_columns from label match: x=${xCol.name}, y=${yCol.name}`);
                return { x: xCol, y: yCol };
            }
        }

        // Last resort: Use column index based on trace name
        const traceMatch = elementName.match(/trace_(\d+)/);
        if (traceMatch) {
            const idx = parseInt(traceMatch[1]) + 1;
            if (idx < headers.length) {
                const xCol = { name: headers[0], index: 0 };
                const yCol = { name: headers[idx], index: idx };
                console.log(`[CsvDataCoordinator] Inferred csv_columns from element name: x=${xCol.name}, y=${yCol.name}`);
                return { x: xCol, y: yCol };
            }
        }

        console.log('[CsvDataCoordinator] Could not infer csv_columns for element:', elementName, 'label:', label);
        return null;
    }
}
