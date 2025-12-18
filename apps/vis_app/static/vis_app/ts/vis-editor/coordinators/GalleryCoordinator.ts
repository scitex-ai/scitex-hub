/**
 * GalleryCoordinator - Handles gallery and plot rendering operations
 *
 * Extracted from VisEditor to maintain single responsibility.
 * Manages gallery initialization, plot rendering, and bundle creation.
 */

import { PlotGallery, GalleryCategories } from '../../vis/index.ts';
import type { CanvasManager } from '../../vis/CanvasManager.ts';
import type { DataTableManager } from '../../vis/DataTableManager.ts';
import type { PropertiesManager } from '../../vis/PropertiesManager.ts';
import type { DataTabManager } from '../../vis/ui/DataTabManager.ts';
import type { EditorCallbackHandlers } from '../EditorCallbackHandlers.ts';
import type { CsvDataCoordinator } from './CsvDataCoordinator.ts';

export interface GalleryCoordinatorDeps {
    canvasManager: CanvasManager;
    dataTableManager: DataTableManager;
    propertiesManager: PropertiesManager;
    dataTabManager: DataTabManager;
    csvDataCoordinator: CsvDataCoordinator;
    callbackHandlers: EditorCallbackHandlers;
    updateStatusBar: (message: string) => void;
    getProjectContext: () => { projectOwner: string; projectSlug: string; figureName: string };
    refreshFilesTree: () => Promise<void>;
}

export interface PlotState {
    currentPlot: any;
    currentPlotType: string;
    currentCategory: string;
    currentCsvData: string[][];
}

export class GalleryCoordinator {
    private deps: GalleryCoordinatorDeps;
    private plotGallery!: PlotGallery;
    private galleryCategories!: GalleryCategories;
    private plotState: PlotState = {
        currentPlot: null,
        currentPlotType: '',
        currentCategory: '',
        currentCsvData: [],
    };

    constructor(deps: GalleryCoordinatorDeps) {
        this.deps = deps;
    }

    /**
     * Get the GalleryCategories instance
     */
    public getGalleryCategories(): GalleryCategories {
        return this.galleryCategories;
    }

    /**
     * Get current plot state
     */
    public getPlotState(): PlotState {
        return this.plotState;
    }

    /**
     * Set current plot state
     */
    public setPlotState(plot: any, plotType: string, category: string, csvData: string[][]): void {
        this.plotState.currentPlot = plot;
        this.plotState.currentPlotType = plotType;
        this.plotState.currentCategory = category;
        this.plotState.currentCsvData = csvData;
    }

    /**
     * Initialize the plot gallery
     */
    public initialize(): void {
        this.galleryCategories = new GalleryCategories({
            onPlotSelect: this.deps.callbackHandlers.createPlotSelectCallback(this.deps.dataTabManager),
            onDataModified: (isModified) => {
                const revertBtn = document.getElementById('revert-data-btn');
                if (revertBtn) {
                    revertBtn.style.display = isModified ? 'flex' : 'none';
                }
            }
        });

        this.galleryCategories.initialize();

        const revertBtn = document.getElementById('revert-data-btn');
        if (revertBtn) {
            revertBtn.addEventListener('click', () => {
                const originalData = this.galleryCategories.revertToOriginal();
                if (originalData) {
                    this.deps.dataTableManager.loadFromArray(originalData, true);
                    this.deps.updateStatusBar('Reverted to original data');
                }
            });
        }

        this.plotGallery = new PlotGallery({
            onSelect: async (plot, gallery) => {
                console.log(`[GalleryCoordinator] Legacy plot selected: ${plot.name} from ${gallery.name}`);
            }
        });

        console.log('[GalleryCoordinator] GalleryCategories initialized');
    }

    /**
     * Re-render current plot with updated properties
     */
    public async reRenderCurrentPlot(): Promise<void> {
        const { currentPlot, currentCsvData, currentPlotType, currentCategory } = this.plotState;

        if (!currentPlot || !currentCsvData || currentCsvData.length < 2) {
            console.warn('[GalleryCoordinator] No current plot to re-render');
            return;
        }

        const props = this.deps.propertiesManager.getPlotProperties();
        const columns = this.deps.propertiesManager.getSelectedColumns();

        const colorInput = document.getElementById('prop-plot-color') as HTMLInputElement;
        const titleInput = document.getElementById('prop-labels-title') as HTMLInputElement;
        const xlabelInput = document.getElementById('prop-labels-x') as HTMLInputElement;
        const ylabelInput = document.getElementById('prop-labels-y') as HTMLInputElement;

        const overrides: Record<string, any> = {
            fig_width: 4,
            fig_height: 3,
            dpi: 150,
            linewidth: props.lineWidth,
            marker_size: props.markerSize,
            x_column: columns.xColumn,
            y_columns: [columns.yColumn],
        };

        if (colorInput?.value) overrides.color = colorInput.value;
        if (titleInput?.value) overrides.title = titleInput.value;
        if (xlabelInput?.value) overrides.xlabel = xlabelInput.value;
        if (ylabelInput?.value) overrides.ylabel = ylabelInput.value;

        try {
            this.deps.updateStatusBar(`Re-rendering ${currentPlot.display_name}...`);

            const response = await fetch('/vis/api/plot/gallery/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plot_type: currentPlotType,
                    category: currentCategory,
                    csv_data: currentCsvData,
                    overrides,
                }),
            });

            const result = await response.json();
            if (result.success && result.image) {
                const axisMetadata = result.axes_bbox_px ? {
                    axes_bbox_px: result.axes_bbox_px,
                    figure_size_px: { width: result.width, height: result.height },
                    element_bboxes: result.element_bboxes,
                    hitmap: result.hitmap,
                    hitmap_color_map: result.hitmap_color_map
                } : undefined;

                await this.deps.canvasManager.addImage(result.image, {
                    scaleToFit: true,
                    name: currentPlot.display_name,
                    axisMetadata: axisMetadata,
                });
                this.deps.updateStatusBar(`Updated: ${currentPlot.display_name}`);
            } else {
                this.deps.updateStatusBar(`Failed to update: ${result.error || 'Unknown error'}`);
            }
        } catch (err) {
            console.error('[GalleryCoordinator] Re-render error:', err);
            this.deps.updateStatusBar('Failed to re-render plot');
        }
    }

    /**
     * Re-render plot at new size
     */
    public async reRenderPlotAtSize(obj: any, newWidth: number, newHeight: number): Promise<void> {
        if (!obj.plotInfo) return;

        const { plot, category } = obj.plotInfo;
        if (!plot || !category) return;

        this.deps.updateStatusBar(`Re-rendering ${obj.name || 'plot'} at ${Math.round(newWidth)}x${Math.round(newHeight)}px...`);

        try {
            if (obj.axisMetadata?.axes_bbox_px && obj.originalWidth && obj.originalHeight) {
                const scaleX = newWidth / obj.originalWidth;
                const scaleY = newHeight / obj.originalHeight;

                obj.scaledAxisMetadata = {
                    axes_bbox_px: {
                        x0: Math.round(obj.axisMetadata.axes_bbox_px.x0 * scaleX),
                        y0: Math.round(obj.axisMetadata.axes_bbox_px.y0 * scaleY),
                        x1: Math.round(obj.axisMetadata.axes_bbox_px.x1 * scaleX),
                        y1: Math.round(obj.axisMetadata.axes_bbox_px.y1 * scaleY),
                        width: Math.round(obj.axisMetadata.axes_bbox_px.width * scaleX),
                        height: Math.round(obj.axisMetadata.axes_bbox_px.height * scaleY)
                    }
                };
            }

            this.deps.propertiesManager.showCanvasObjectProperties(obj);
            this.deps.updateStatusBar(`Resized: ${obj.name || 'plot'}`);
        } catch (error) {
            this.deps.updateStatusBar(`Failed to re-render: ${obj.name || 'plot'}`);
        }
    }

    /**
     * Create a pltz bundle from gallery selection
     */
    public async createPltzBundleFromGallery(
        plot: any,
        category: string,
        csvData?: string[][]
    ): Promise<void> {
        const { projectOwner, projectSlug, figureName } = this.deps.getProjectContext();

        this.deps.updateStatusBar(`Creating bundle: ${plot.display_name}...`);

        const plotType = this.mapPlotNameToType(plot.name, category);

        let dataCsv: string | undefined;
        if (csvData && csvData.length > 1) {
            dataCsv = csvData.map(row => row.join(',')).join('\n');
        }

        try {
            const result = await this.deps.canvasManager.addPanelFromGallery(
                plotType,
                dataCsv,
                projectOwner,
                projectSlug,
                figureName,
                category,
                plot.name
            );

            if (result) {
                this.deps.updateStatusBar(`Panel ${result.panelLabel} created: ${plot.display_name}`);
                await this.deps.refreshFilesTree();
            } else {
                this.deps.updateStatusBar(`Error: Failed to create bundle for ${plot.display_name}`);
            }
        } catch (error) {
            console.error('[GalleryCoordinator] Failed to create pltz bundle:', error);
            this.deps.updateStatusBar(`Error: ${error}`);
        }
    }

    /**
     * Map plot name to plot type
     */
    public mapPlotNameToType(plotName: string, category: string): string {
        const directMappings: Record<string, string> = {
            'plot': 'line',
            'stx_line': 'line',
            'stx_shaded_line': 'line',
            'stx_plot': 'line',
        };

        const lowerName = plotName.toLowerCase();
        if (directMappings[lowerName]) return directMappings[lowerName];

        const parts = lowerName.split('_');
        const plotTypes = [
            'line', 'scatter', 'bar', 'barh', 'histogram', 'hist',
            'boxplot', 'violinplot', 'heatmap', 'contour', 'pie',
            'step', 'stem', 'area', 'kde', 'ecdf'
        ];

        for (const type of plotTypes) {
            if (parts[0] === type || lowerName.includes(type)) return type;
        }

        const categoryMap: Record<string, string> = {
            'line': 'line',
            'scatter': 'scatter',
            'bar': 'bar',
            'distribution': 'histogram',
            'statistical': 'boxplot',
            'heatmap': 'heatmap',
            'contour': 'contour',
            'pie': 'pie',
            'vector': 'line',
            'error': 'line',
            'stem': 'stem',
        };

        return categoryMap[category.toLowerCase()] || 'line';
    }

    /**
     * Debug: Load all plot types
     */
    public async plotAllTypes(): Promise<void> {
        console.log('[GalleryCoordinator] Loading all plot types for debugging...');
        this.deps.updateStatusBar('Loading all plot types...');

        try {
            const response = await fetch('/vis/api/gallery/available/');
            if (!response.ok) throw new Error(`API error: ${response.status}`);

            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'Failed to load categories');

            const allPlots: Array<{ name: string; category: string; png: string; svg: string; csv: string }> = [];
            for (const [catId, catInfo] of Object.entries(data.categories)) {
                const info = catInfo as { name: string; plots: string[] };
                for (const plotName of info.plots) {
                    allPlots.push({
                        name: plotName,
                        category: catId,
                        png: `/vis/api/gallery/project/${catId}/${plotName}/image/?format=binary`,
                        svg: `/vis/api/gallery/project/${catId}/${plotName}/image/?format=svg`,
                        csv: `/vis/api/gallery/project/${catId}/${plotName}/csv/`,
                    });
                }
            }

            const PLOT_WIDTH = 180;
            const PLOT_HEIGHT = 140;
            const COLS = 6;
            const MARGIN = 20;
            const START_X = 50;
            const START_Y = 50;

            for (let i = 0; i < allPlots.length; i++) {
                const plot = allPlots[i];
                const col = i % COLS;
                const row = Math.floor(i / COLS);
                const x = START_X + col * (PLOT_WIDTH + MARGIN);
                const y = START_Y + row * (PLOT_HEIGHT + MARGIN);

                try {
                    let csvData: string[][] = [];
                    try {
                        const csvResponse = await fetch(plot.csv);
                        if (csvResponse.ok) {
                            const csvText = await csvResponse.text();
                            csvData = this.deps.csvDataCoordinator.parseCSV(csvText);
                        }
                    } catch {
                        // No CSV available
                    }

                    const metaUrl = `/vis/api/gallery/metadata/${plot.category}/${plot.name}/`;
                    let axisMetadata: any = undefined;
                    try {
                        const metaResponse = await fetch(metaUrl);
                        if (metaResponse.ok) {
                            const metadata = await metaResponse.json();
                            if (metadata.success && metadata.axes_bbox_px) {
                                axisMetadata = {
                                    axes_bbox_px: metadata.axes_bbox_px,
                                    figure_size_px: metadata.figure_size_px,
                                    element_bboxes: metadata.element_bboxes,
                                    hitmap: metadata.hitmap,
                                    hitmap_color_map: metadata.hitmap_color_map
                                };
                            }
                        }
                    } catch {
                        // No metadata available
                    }

                    await this.deps.canvasManager.addSvgFromUrl(plot.svg, {
                        left: x,
                        top: y,
                        scaleToFit: true,
                        maxWidth: PLOT_WIDTH,
                        maxHeight: PLOT_HEIGHT,
                        name: `${plot.category}/${plot.name}`,
                        axisMetadata: axisMetadata,
                        plotInfo: { category: plot.category, name: plot.name, plotType: plot.name },
                        csvData: csvData,
                    });
                } catch (err) {
                    console.error(`[GalleryCoordinator] Failed to load ${plot.name}:`, err);
                }
            }

            this.deps.updateStatusBar(`Loaded ${allPlots.length} plot types`);
        } catch (error) {
            console.error('[GalleryCoordinator] Failed to load all plot types:', error);
            this.deps.updateStatusBar('Failed to load all plot types');
        }
    }
}
