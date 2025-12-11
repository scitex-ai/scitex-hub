/**
 * SciTeX Sigma Editor - Main Coordinator Class
 *
 * Lightweight coordinator that:
 * - Initializes all manager modules
 * - Connects managers through callbacks
 * - Maintains overall editor state
 */

import {
    RulersManager,
    CanvasManager,
    DataTableManager,
    PropertiesManager,
    UIManager,
    DataTabManager,
    CanvasTabManager,
    FigureDropHandler,
    SciTeXEditor,
    PlotGallery,
    GalleryCategories,
} from '../vis/index.ts';

import { setupGraphOperations } from './graph.ts';

/**
 * SigmaEditor - Coordinator class that manages all editor components
 */
export class SigmaEditor {
    // Manager instances
    private rulersManager!: RulersManager;
    private canvasManager!: CanvasManager;
    private dataTableManager!: DataTableManager;
    private propertiesManager!: PropertiesManager;
    private uiManager!: UIManager;
    private dataTabManager!: DataTabManager;
    private canvasTabManager!: CanvasTabManager;

    // SciTeX integration
    private figureDropHandler!: FigureDropHandler;
    private scitexEditor!: SciTeXEditor;
    private plotGallery!: PlotGallery;
    private galleryCategories!: GalleryCategories;

    // Plot-related state
    private currentPlot: any = null;
    private currentPlotType: string = '';
    private currentCategory: string = '';
    private currentCsvData: string[][] = [];

    // Tab-Figure synchronization: Map tabId <-> canvasObjectId
    private tabToFigureMap: Map<string, string> = new Map();
    private figureToTabMap: Map<string, string> = new Map();
    private isDeleting: boolean = false; // Prevent recursive deletion

    // Shared references for managers
    private firstRowIsHeader: boolean = true;
    private firstColIsIndex: boolean = false;

    constructor() {
        console.log('[SigmaEditor] Initializing modular Sigma Editor...');

        // Initialize managers
        this.initializeManagers();

        // Initialize all components
        this.initializeEditor();
    }

    /**
     * Initialize all manager instances
     */
    private initializeManagers(): void {
        // Initialize CanvasManager
        this.canvasManager = new CanvasManager(
            (message: string) => this.updateStatusBar(message),
            () => this.updateRulersAreaTransform()
        );

        // Initialize RulersManager
        this.rulersManager = new RulersManager(
            null,
            (message: string) => this.updateStatusBar(message)
        );

        // Initialize DataTableManager
        this.dataTableManager = new DataTableManager(
            (message: string) => this.updateStatusBar(message),
            () => this.propertiesManager.updateColumnDropdowns(),
            () => this.updateRulersAreaTransform()
        );

        // Initialize PropertiesManager
        this.propertiesManager = new PropertiesManager(
            () => this.dataTableManager.getCurrentData()
        );

        // Initialize UIManager
        this.uiManager = new UIManager(
            (file: File) => this.dataTableManager.handleFileImport(file),
            () => this.dataTableManager.loadDemoData(),
            (count: number) => this.dataTableManager.addColumns(count),
            (count: number) => this.dataTableManager.addRows(count),
            () => (this.dataTableManager as any)['copySelectionToClipboard'](),
            (plotType: string) => this.createQuickPlot(plotType),
            () => this.canvasManager.zoomIn(),
            () => this.canvasManager.zoomOut(),
            () => this.canvasManager.zoomToFit(),
            () => this.canvasManager.toggleGrid(),
            { value: this.firstRowIsHeader },
            { value: this.firstColIsIndex },
            () => this.dataTableManager.renderEditableDataTable(),
            (message: string) => this.updateStatusBar(message),
            () => this.deleteSelectedObject(),
            () => this.duplicateSelectedObject(),
            () => this.canvasManager.undo(),
            () => this.canvasManager.redo(),
            () => this.canvasManager.copyActiveObject(),
            () => this.canvasManager.pasteObject(),
            (direction) => this.canvasManager.alignObjects(direction),
            (action) => this.canvasManager.arrangeObject(action),
            (direction) => this.canvasManager.distributeObjects(direction),
            (action) => this.handleSizeAction(action),
            () => this.canvasManager.groupObjects(),
            () => this.canvasManager.ungroupObjects(),
            () => this.canvasManager.copyView(),
            () => this.canvasManager.pasteView(),
            (direction, shift) => this.canvasManager.nudgeObjects(direction, shift),
            () => this.canvasManager.selectAll(),
            (direction: 'L' | 'C' | 'R' | 'T' | 'M' | 'B' | 'S') => {
                if (direction === 'S') {
                    this.canvasManager.stackVertically();
                } else {
                    this.canvasManager.alignByAxis(direction);
                }
            },
            () => this.canvasManager.exitElementSelectionMode()  // escapeCallback
        );

        // Initialize DataTabManager
        this.dataTabManager = new DataTabManager();
        this.dataTabManager.setCallbacks(
            (tabId: string) => {
                console.log('[SigmaEditor] Data tab changed to:', tabId);
                // Load the tab's data into the data table
                const tabData = this.dataTabManager.getTabData(tabId);
                if (tabData && Array.isArray(tabData) && tabData.length > 0) {
                    this.dataTableManager.loadFromArray(tabData, true);
                    this.updateStatusBar(`Loaded data for tab`);
                }
            },
            (tabId: string) => {
                console.log('[SigmaEditor] Data tab closed:', tabId);
                // Remove corresponding figure from canvas (if not already being deleted)
                if (!this.isDeleting) {
                    const figureId = this.tabToFigureMap.get(tabId);
                    if (figureId) {
                        this.isDeleting = true;
                        this.removeFigureById(figureId);
                        this.tabToFigureMap.delete(tabId);
                        this.figureToTabMap.delete(figureId);
                        this.isDeleting = false;
                    }
                }
            },
            (tabId: string, newName: string) => {
                console.log('[SigmaEditor] Data tab renamed:', tabId, 'to', newName);
            }
        );

        // Initialize CanvasTabManager
        this.canvasTabManager = new CanvasTabManager();
        this.canvasTabManager.setCallbacks(
            async (tabId: string) => {
                console.log('[SigmaEditor] Canvas tab changed to:', tabId);
                // Restore canvas content for the new tab
                await this.restoreCanvasForTab(tabId);
                const activeTab = this.canvasTabManager.getActiveTab();
                if (activeTab) {
                    this.updateStatusBar(`Switched to ${activeTab.figureName}`);
                }
            },
            (tabId: string) => {
                console.log('[SigmaEditor] Canvas tab closed:', tabId);
                // Tab data is already removed by CanvasTabManager
            },
            (tabId: string, newName: string) => {
                console.log('[SigmaEditor] Canvas tab renamed:', tabId, 'to', newName);
            },
            () => {
                // onBeforeTabChange: Save current canvas before switching
                this.saveCanvasForCurrentTab();
            }
        );
    }

    /**
     * Save current canvas state to the active tab
     */
    private saveCanvasForCurrentTab(): void {
        if (!this.canvasManager.canvas) return;

        const json = this.canvasManager.canvas.toJSON(['name', 'id', 'axisMetadata', 'plotInfo', 'originalWidth', 'originalHeight', 'csvData']);
        const viewState = {
            zoom: this.canvasManager.getCanvasZoomLevel(),
            panX: this.canvasManager.getCanvasPanOffset().x,
            panY: this.canvasManager.getCanvasPanOffset().y
        };

        this.canvasTabManager.saveCanvasState(json, viewState);
    }

    /**
     * Restore canvas content from a specific tab
     */
    private async restoreCanvasForTab(tabId: string): Promise<void> {
        const tabState = this.canvasTabManager.getTabState(tabId);
        if (!tabState || !this.canvasManager.canvas) {
            // New tab or no state - clear canvas
            this.canvasManager.canvas?.clear();
            this.canvasManager.canvas?.renderAll();
            console.log('[SigmaEditor] New tab - canvas cleared');
            return;
        }

        if (tabState.canvasJson) {
            // Load canvas content from tab state
            return new Promise((resolve) => {
                this.canvasManager.canvas!.loadFromJSON(tabState.canvasJson, () => {
                    // Restore view state
                    if (tabState.viewState) {
                        this.canvasManager.setCanvasZoomLevel(tabState.viewState.zoom);
                        this.canvasManager.setCanvasPanOffset(tabState.viewState.panX, tabState.viewState.panY);
                    }
                    this.canvasManager.canvas!.renderAll();
                    this.updateRulersAreaTransform();
                    console.log(`[SigmaEditor] Restored canvas for tab ${tabId}`);
                    resolve();
                });
            });
        }
    }

    /**
     * Initialize editor components using parallel execution for independent tasks
     */
    private async initializeEditor(): Promise<void> {
        const totalStart = performance.now();
        console.log('[SigmaEditor] Starting optimized initialization...');

        // PHASE 1: CRITICAL PATH ONLY
        const phase1Start = performance.now();

        this.uiManager.initializeEventListeners();
        this.dataTabManager.initializeEventListeners();
        this.dataTabManager.renderTabs();

        // Load canvas tabs from storage (if any)
        this.canvasTabManager.loadTabsFromStorage();
        this.canvasTabManager.initializeEventListeners();
        this.canvasTabManager.renderTabs();
        this.dataTableManager.initializeBlankTable();

        const phase1End = performance.now();
        console.log(`[SigmaEditor] Phase 1 complete in ${(phase1End - phase1Start).toFixed(2)}ms`);

        // PHASE 2: DEFERRED
        const phase2Start = performance.now();
        await new Promise(resolve => setTimeout(resolve, 0));

        this.setupDataTableEvents();
        this.dataTableManager.setupColumnResizing();
        this.uiManager.setupKeyboardShortcuts();

        const phase2End = performance.now();
        console.log(`[SigmaEditor] Phase 2 complete in ${(phase2End - phase2Start).toFixed(2)}ms`);

        // PHASE 3: DEFERRED - Canvas and heavy graphics
        const phase3Start = performance.now();
        await new Promise(resolve => setTimeout(resolve, 0));

        this.canvasManager.initCanvas();
        this.canvasManager.setupCanvasEvents();

        // Wire up selection callback to update properties panel and data tab
        this.canvasManager.setSelectionCallback(async (obj: any) => {
            if (obj) {
                this.propertiesManager.showCanvasObjectProperties(obj);

                // Handle CSV data in dedicated tab
                if (obj.csvData) {
                    this.loadCsvDataInTab(obj);
                } else if (obj.name) {
                    // Try to fetch CSV data from gallery based on object name
                    await this.loadCsvForImage(obj);
                }
            } else {
                this.propertiesManager.showNoSelection();
            }
        });

        // Wire up resize callback to re-render plots at new size
        this.canvasManager.setObjectResizedCallback(async (obj: any, newWidth: number, newHeight: number) => {
            await this.reRenderPlotAtSize(obj, newWidth, newHeight);
        });

        // Wire up element selection callback to highlight CSV columns and show properties
        this.canvasManager.setElementSelectionCallback((elementNames: string[], elementInfos: any[]) => {
            if (elementNames.length > 0 && elementInfos.length > 0) {
                // Use first selected element for properties panel (or could show multi-select)
                const elementName = elementNames[0];
                const elementInfo = elementInfos[0];

                console.log(`[SigmaEditor] Elements selected: ${elementNames.join(', ')}`, elementInfos);

                // Show element properties in right panel
                this.propertiesManager.showElementProperties(elementName, elementInfo);

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
                        csvCols = this.inferCsvColumnsFromLabel(elementNames[i], info);
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
                    console.log(`[SigmaEditor] Highlighting columns: ${columnIndices.join(', ')}`);
                    // Highlight the corresponding columns in the data table
                    this.dataTableManager.highlightColumns(columnIndices);

                    // Update status bar with column info
                    const uniqueNames = [...new Set(allColumnNames)];
                    const colNamesStr = uniqueNames.join(', ');
                    if (elementNames.length === 1) {
                        this.updateStatusBar(`Element: ${elementInfo.label || elementName} (columns: ${colNamesStr})`);
                    } else {
                        this.updateStatusBar(`${elementNames.length} elements selected (columns: ${colNamesStr})`);
                    }
                } else {
                    console.log(`[SigmaEditor] No csv_columns on selected elements`);
                    // Update status bar without column info
                    if (elementNames.length === 1) {
                        this.updateStatusBar(`Element: ${elementInfo.label || elementName}`);
                    } else {
                        this.updateStatusBar(`${elementNames.length} elements selected`);
                    }
                }
            } else {
                // Clear highlights when no element selected
                this.dataTableManager.clearColumnHighlights();
            }
        });

        this.rulersManager['canvas'] = this.canvasManager.canvas;
        this.rulersManager.initializeRulers();

        // Set up bidirectional sync between RulersManager and CanvasManager
        this.rulersManager.setTransformCallback(() => {
            // Sync pan offset from RulersManager to CanvasManager
            const rulerPan = this.rulersManager.getCanvasPanOffset();
            this.canvasManager.setCanvasPanOffset(rulerPan.x, rulerPan.y);
            // Update the transform using CanvasManager's values
            this.updateRulersAreaTransform();
        });

        this.rulersManager.setupRulerDragging();

        // Apply initial transform to rulers-area to match CanvasManager's initial zoom (0.22)
        this.updateRulersAreaTransform();

        // Note: Ruler unit toggle is now handled by clicking on ruler labels (0mm, 10mm, etc.)
        // See RulersManager.setupRulerLabelClickHandlers()

        // Initialize FigureDropHandler with CanvasManager
        this.figureDropHandler = new FigureDropHandler({
            canvasSelector: '#canvas-container',
            dataTableSelector: '.data-table-container',
            canvasManager: this.canvasManager,
            onCsvLoad: (data: string[][]) => {
                console.log('[SigmaEditor] CSV loaded via drop:', data.length, 'rows');
                // TODO: Load into data table
            },
        });

        // Restore canvas content from active tab or fallback to old localStorage
        setTimeout(async () => {
            const activeTab = this.canvasTabManager.getActiveTab();
            if (activeTab?.canvasJson) {
                // Restore from canvas tab state
                await this.restoreCanvasForTab(activeTab.id);
                console.log(`[SigmaEditor] Restored canvas from tab: ${activeTab.figureName}`);
            } else {
                // Fallback: Try to restore from old single-canvas localStorage
                const savedState = localStorage.getItem('scitex-vis-viewstate');
                if (savedState) {
                    const restoredObjects = await this.canvasManager.restoreCanvasContent();
                    await this.loadMissingMetadata(restoredObjects);
                    this.updateRulersAreaTransform();
                    console.log(`[SigmaEditor] Restored view: ${Math.round(this.canvasManager.getCanvasZoomLevel() * 100)}%`);

                    // Migrate: Save this to the default tab
                    this.saveCanvasForCurrentTab();
                } else {
                    // First time - zoom to fit
                    this.canvasManager.zoomToFit();
                    this.updateRulersAreaTransform();
                    console.log(`[SigmaEditor] Initial zoom: ${Math.round(this.canvasManager.getCanvasZoomLevel() * 100)}%`);
                }
            }

            // Re-apply canvas theme AFTER content restoration
            // This ensures the theme is not overwritten by saved canvas JSON
            const savedGlobalTheme = localStorage.getItem('scitex-theme-preference') || 'dark';
            const savedCanvasTheme = localStorage.getItem('canvas-theme') || savedGlobalTheme;
            const canvasDarkMode = savedCanvasTheme === 'dark';
            this.canvasManager.updateCanvasTheme(canvasDarkMode);
            console.log(`[SigmaEditor] Canvas theme re-applied after restore: ${savedCanvasTheme}`);

            // Redraw rulers after canvas is fully loaded
            this.rulersManager.drawRulers();
            console.log(`[SigmaEditor] Rulers redrawn after canvas restore`);
        }, 100);

        const phase3End = performance.now();
        console.log(`[SigmaEditor] Phase 3 complete in ${(phase3End - phase3Start).toFixed(2)}ms`);

        // PHASE 4: DEFERRED - Properties and final setup
        const phase4Start = performance.now();
        await new Promise(resolve => setTimeout(resolve, 0));

        this.propertiesManager.initPropertiesTabs();
        this.propertiesManager.setupPropertySliders();
        this.uiManager.setPropertiesManager(this.propertiesManager);
        this.uiManager.setDataTableManager(this.dataTableManager);
        this.uiManager.initializeTreeManager();

        // Initialize PlotGallery for thumbnail dropdowns
        this.initializePlotGallery();

        // Setup property change handlers for live preview
        this.setupPropertyChangeHandlers();

        this.updateStatusBar('Ready');

        const phase4End = performance.now();
        console.log(`[SigmaEditor] Phase 4 complete in ${(phase4End - phase4Start).toFixed(2)}ms`);

        // Note: Canvas theme is applied in the setTimeout callback after canvas content restoration
        // to ensure it's not overwritten by saved canvas JSON

        // Listen for global theme changes to update rulers
        document.addEventListener('theme-changed', (e: CustomEvent) => {
            const isDark = e.detail?.theme === 'dark';
            this.rulersManager.updateRulerTheme(isDark);
            console.log(`[SigmaEditor] Global theme changed, rulers updated to ${isDark ? 'dark' : 'light'}`);
        });

        const totalEnd = performance.now();
        console.log(`[SigmaEditor] Total initialization: ${(totalEnd - totalStart).toFixed(2)}ms`);
    }

    /**
     * Setup data table events
     */
    private setupDataTableEvents(): void {
        console.log('[SigmaEditor] Data table using native scrolling');
    }

    /**
     * Setup property change handlers for live preview
     */
    private setupPropertyChangeHandlers(): void {
        // Use MutationObserver to watch for dynamically added property elements
        const dynamicPropsEl = document.getElementById('dynamic-properties');
        if (!dynamicPropsEl) return;

        // Debounce helper
        let reRenderTimeout: ReturnType<typeof setTimeout> | null = null;
        const debounceReRender = () => {
            if (reRenderTimeout) clearTimeout(reRenderTimeout);
            reRenderTimeout = setTimeout(() => {
                this.reRenderCurrentPlot();
            }, 500); // Wait 500ms after last change
        };

        // Watch for property changes
        const observer = new MutationObserver(() => {
            // Setup handlers for newly added elements
            this.setupPropertyInputHandlers(debounceReRender);
        });

        observer.observe(dynamicPropsEl, { childList: true, subtree: true });

        // Initial setup
        this.setupPropertyInputHandlers(debounceReRender);
        console.log('[SigmaEditor] Property change handlers initialized');
    }

    /**
     * Setup handlers for property input elements
     */
    private setupPropertyInputHandlers(onChange: () => void): void {
        const propsContainer = document.getElementById('dynamic-properties');
        if (!propsContainer) return;

        // Range sliders
        propsContainer.querySelectorAll('input[type="range"]').forEach(slider => {
            if ((slider as any)._hasChangeHandler) return;
            slider.addEventListener('change', onChange);
            (slider as any)._hasChangeHandler = true;
        });

        // Color pickers
        propsContainer.querySelectorAll('input[type="color"]').forEach(picker => {
            if ((picker as any)._hasChangeHandler) return;
            picker.addEventListener('change', onChange);
            (picker as any)._hasChangeHandler = true;
        });

        // Select dropdowns
        propsContainer.querySelectorAll('select').forEach(select => {
            if ((select as any)._hasChangeHandler) return;
            select.addEventListener('change', onChange);
            (select as any)._hasChangeHandler = true;
        });

        // Text inputs (with debounce)
        propsContainer.querySelectorAll('input[type="text"], input[type="number"]').forEach(input => {
            if ((input as any)._hasChangeHandler) return;
            input.addEventListener('change', onChange);
            (input as any)._hasChangeHandler = true;
        });
    }

    /**
     * Update rulers area transform
     * Syncs transform state between CanvasManager and RulersManager
     */
    private updateRulersAreaTransform(): void {
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
        if (!rulersArea) return;

        const zoom = this.canvasManager.getCanvasZoomLevel();
        const pan = this.canvasManager.getCanvasPanOffset();

        // Sync state to RulersManager for bidirectional consistency
        this.rulersManager.setCanvasZoomLevel(zoom);
        this.rulersManager.setCanvasPanOffset(pan);

        rulersArea.style.transform = `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`;
        rulersArea.style.transformOrigin = '0 0';
    }

    /**
     * Update status bar
     */
    private updateStatusBar(message?: string): void {
        this.uiManager.updateStatusBar(message);
    }

    /**
     * Create quick plot (delegates to graph module)
     */
    private createQuickPlot(plotType: string): void {
        const currentData = this.dataTableManager.getCurrentData();
        if (!currentData || currentData.rows.length === 0) {
            this.updateStatusBar('Please load data first');
            return;
        }

        console.log(`[SigmaEditor] Creating ${plotType} plot...`);
        this.updateStatusBar(`Creating ${plotType} plot...`);

        const graphOps = setupGraphOperations(
            this.dataTableManager,
            this.propertiesManager,
            (msg) => this.updateStatusBar(msg)
        );

        this.currentPlot = graphOps.renderPlot(plotType);
        this.currentPlotType = plotType;
    }

    /**
     * Update canvas theme
     * Note: Rulers follow global theme, not canvas theme
     */
    public updateCanvasTheme(isDark: boolean): void {
        this.canvasManager.updateCanvasTheme(isDark);
        // Rulers follow global theme, not canvas theme - do not update here
    }

    /**
     * Update global UI theme (including rulers)
     * Called when global theme changes
     */
    public updateGlobalTheme(isDark: boolean): void {
        this.rulersManager.updateRulerTheme(isDark);
    }

    /**
     * Delete selected object from canvas
     */
    public deleteSelectedObject(): void {
        // Set flag to prevent recursive deletion
        this.isDeleting = true;

        // Get selected objects before deleting to close corresponding tabs
        const activeObj = this.canvasManager.canvas?.getActiveObject();
        if (activeObj) {
            // Handle single or multiple selection
            const objects = activeObj.type === 'activeSelection'
                ? (activeObj as any).getObjects()
                : [activeObj];

            // Close corresponding tabs for deleted figures
            for (const obj of objects) {
                const objId = obj.id;
                if (objId) {
                    const tabId = this.figureToTabMap.get(objId);
                    if (tabId) {
                        this.dataTabManager.closeTab(tabId);
                        this.figureToTabMap.delete(objId);
                        this.tabToFigureMap.delete(tabId);
                    }
                }
            }
        }

        this.canvasManager.removeActiveObject();
        this.canvasManager.saveCanvasContent();
        this.isDeleting = false;
        this.updateStatusBar('Object deleted');
    }

    /**
     * Remove a figure from canvas by its ID
     */
    private removeFigureById(figureId: string): void {
        if (!this.canvasManager.canvas) return;

        const objects = this.canvasManager.canvas.getObjects();
        const figure = objects.find((obj: any) => obj.id === figureId);
        if (figure) {
            this.canvasManager.canvas.remove(figure);
            this.canvasManager.canvas.renderAll();
            this.canvasManager.saveCanvasContent();
            this.updateStatusBar('Figure removed');
        }
    }

    /**
     * Duplicate selected object on canvas
     */
    public duplicateSelectedObject(): void {
        this.canvasManager.duplicateActiveObject();
    }

    /**
     * Handle size actions from keyboard shortcuts
     */
    private handleSizeAction(action: 'match-size' | 'match-width' | 'match-height' | 'multiple-crop'): void {
        switch (action) {
            case 'match-size':
                this.canvasManager.matchSize();
                break;
            case 'match-width':
                this.canvasManager.matchWidth();
                break;
            case 'match-height':
                this.canvasManager.matchHeight();
                break;
            case 'multiple-crop':
                this.canvasManager.multipleCrop();
                break;
        }
    }

    /**
     * Get tab type from gallery category
     * Maps category names to DataTab types for icon synchronization
     */
    private getTabTypeFromCategory(category: string): 'line' | 'scatter' | 'categorical' | 'distribution' | 'statistical' | 'grid' | 'area' | 'contour' | 'vector' | 'special' | 'default' {
        const lowerCategory = category.toLowerCase();
        switch (lowerCategory) {
            case 'line':
                return 'line';
            case 'scatter':
                return 'scatter';
            case 'categorical':
                return 'categorical';
            case 'distribution':
                return 'distribution';
            case 'statistical':
                return 'statistical';
            case 'grid':
                return 'grid';
            case 'area':
                return 'area';
            case 'contour':
                return 'contour';
            case 'vector':
                return 'vector';
            case 'special':
                return 'special';
            default:
                return 'default';
        }
    }

    /**
     * Initialize PlotGallery and GalleryCategories
     */
    private initializePlotGallery(): void {
        // Initialize GalleryCategories for the new category-based UI
        this.galleryCategories = new GalleryCategories({
            onPlotSelect: async (plot, category, csvData) => {
                console.log(`[SigmaEditor] Gallery plot selected: ${plot.name} (${category})`);
                console.log(`[SigmaEditor] CSV data rows: ${csvData?.length || 0}`);
                this.updateStatusBar(`Loading: ${plot.display_name}...`);

                // Store current plot info for re-rendering
                this.currentPlot = plot;
                this.currentPlotType = plot.name;
                this.currentCategory = category;
                this.currentCsvData = csvData || [];

                // Show properties panel with plot settings
                this.propertiesManager.showPropertiesFor('plot', plot.display_name, {
                    plotType: plot.name,
                    category: category,
                });
                this.propertiesManager.updateColumnDropdowns();

                // Create new tab and load CSV data into data table
                if (csvData && csvData.length > 0) {
                    try {
                        // Determine tab type from category for icon synchronization
                        const tabType = this.getTabTypeFromCategory(category);

                        // Create new tab with the plot data
                        const tabId = this.dataTabManager.createAndSwitchToTab(
                            plot.display_name,
                            tabType,
                            category.charAt(0).toUpperCase() + category.slice(1), // Capitalize category
                            plot.display_name,
                            csvData
                        );

                        // Load CSV into data table
                        this.dataTableManager.loadFromArray(csvData, true);
                        console.log(`[SigmaEditor] Created tab ${tabId} and loaded ${csvData.length} rows from gallery CSV`);
                    } catch (err) {
                        console.error('[SigmaEditor] Failed to load CSV into data table:', err);
                    }
                } else {
                    console.warn('[SigmaEditor] No CSV data to load');
                }

                // Always use static image from gallery - this ensures visual consistency
                // Dynamic re-rendering will only happen when user explicitly modifies data
                await this.loadStaticImage(plot, category, csvData);
            },
            onDataModified: (isModified) => {
                // Update UI to show modification status
                const revertBtn = document.getElementById('revert-data-btn');
                if (revertBtn) {
                    revertBtn.style.display = isModified ? 'flex' : 'none';
                }
            }
        });

        // Initialize the gallery categories UI
        this.galleryCategories.initialize();

        // Setup revert button handler
        const revertBtn = document.getElementById('revert-data-btn');
        if (revertBtn) {
            revertBtn.addEventListener('click', () => {
                const originalData = this.galleryCategories.revertToOriginal();
                if (originalData) {
                    this.dataTableManager.loadFromArray(originalData, true);
                    this.updateStatusBar('Reverted to original data');
                }
            });
        }

        // Also keep the legacy PlotGallery for backward compatibility
        this.plotGallery = new PlotGallery({
            onSelect: async (plot, gallery) => {
                console.log(`[SigmaEditor] Legacy plot selected: ${plot.name} from ${gallery.name}`);
            }
        });

        console.log('[SigmaEditor] GalleryCategories initialized');
    }

    /**
     * Re-render current plot with updated properties
     */
    public async reRenderCurrentPlot(): Promise<void> {
        if (!this.currentPlot || !this.currentCsvData || this.currentCsvData.length < 2) {
            console.warn('[SigmaEditor] No current plot to re-render');
            return;
        }

        // Get current properties from UI
        const props = this.propertiesManager.getPlotProperties();
        const columns = this.propertiesManager.getSelectedColumns();

        // Get additional properties from UI
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

        if (colorInput?.value) {
            overrides.color = colorInput.value;
        }
        if (titleInput?.value) {
            overrides.title = titleInput.value;
        }
        if (xlabelInput?.value) {
            overrides.xlabel = xlabelInput.value;
        }
        if (ylabelInput?.value) {
            overrides.ylabel = ylabelInput.value;
        }

        try {
            this.updateStatusBar(`Re-rendering ${this.currentPlot.display_name}...`);

            const response = await fetch('/vis/api/plot/gallery/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plot_type: this.currentPlotType,
                    category: this.currentCategory,
                    csv_data: this.currentCsvData,
                    overrides,
                }),
            });

            const result = await response.json();
            if (result.success && result.image) {
                // Build axis metadata from response
                const axisMetadata = result.axes_bbox_px ? {
                    axes_bbox_px: result.axes_bbox_px,
                    figure_size_px: { width: result.width, height: result.height },
                    element_bboxes: result.element_bboxes
                } : undefined;

                await this.canvasManager.addImage(result.image, {
                    scaleToFit: true,
                    name: this.currentPlot.display_name,
                    axisMetadata: axisMetadata,
                });
                this.updateStatusBar(`Updated: ${this.currentPlot.display_name}`);
            } else {
                console.error('[SigmaEditor] Re-render failed:', result.error);
                this.updateStatusBar(`Failed to update: ${result.error || 'Unknown error'}`);
            }
        } catch (err) {
            console.error('[SigmaEditor] Re-render error:', err);
            this.updateStatusBar('Failed to re-render plot');
        }
    }

    /**
     * Load static image from gallery
     * Also tries to load JSON metadata for axis snap/align and element selection
     * Prefers SVG format for element selection capability
     */
    private async loadStaticImage(plot: any, category: string, csvData?: string[][]): Promise<void> {
        // Prefer SVG for element selection; fall back to PNG
        const imageUrl = plot.svg || plot.png || `/vis/api/gallery/project/${category}/${plot.name}/image/?format=svg`;
        const isSvg = imageUrl.includes('format=svg') || imageUrl.endsWith('.svg');
        console.log(`[SigmaEditor] Loading static image (${isSvg ? 'SVG' : 'PNG'}): ${imageUrl}`);

        // Try to load JSON metadata from original gallery
        let axisMetadata: any = undefined;
        try {
            // Map category to gallery folder - use API to get metadata
            const metadataResponse = await fetch(`/vis/api/gallery/metadata/${category}/${plot.name}/`);
            if (metadataResponse.ok) {
                const metadata = await metadataResponse.json();
                if (metadata.success && metadata.axes_bbox_px) {
                    axisMetadata = {
                        axes_bbox_px: metadata.axes_bbox_px,
                        figure_size_px: metadata.figure_size_px,
                        element_bboxes: metadata.element_bboxes  // For element-level selection
                    };
                    console.log(`[SigmaEditor] Loaded axis metadata for ${plot.name}:`, axisMetadata);
                    if (metadata.element_bboxes) {
                        console.log(`[SigmaEditor] Element bboxes available: ${Object.keys(metadata.element_bboxes).length} elements`);
                    }
                }
            }
        } catch (err) {
            console.log(`[SigmaEditor] No metadata available for ${plot.name}`);
        }

        try {
            // If no csvData provided, try to fetch from plot.csv before adding image
            // CSV data MUST be passed to addImage so it's set before selection events fire
            let finalCsvData = csvData;
            if ((!finalCsvData || finalCsvData.length === 0) && plot.csv) {
                try {
                    const csvResponse = await fetch(plot.csv);
                    if (csvResponse.ok) {
                        const csvText = await csvResponse.text();
                        finalCsvData = this.parseCSV(csvText);
                        console.log(`[SigmaEditor] Loaded CSV data from ${plot.csv}: ${finalCsvData.length} rows`);
                    }
                } catch (e) {
                    console.log(`[SigmaEditor] No CSV data for ${plot.name}`);
                }
            }

            // Use SVG loader for SVG files (enables element selection), PNG for others
            // Pass metadata through options so it's attached BEFORE setActiveObject
            // This ensures selection:created can detect axisMetadata for element selection mode
            let result: any;
            if (isSvg) {
                result = await this.canvasManager.addSvgFromUrl(imageUrl, {
                    scaleToFit: true,
                    name: plot.display_name,
                    selectableElements: false,  // Group SVG as single object for now
                    axisMetadata: axisMetadata,
                    csvData: finalCsvData,
                    plotInfo: { plot, category },
                });
                // Log metadata attachment (now happens inside addSvgFromUrl)
                if (result && !Array.isArray(result)) {
                    console.log(`[SigmaEditor] Attached metadata to SVG group:`, {
                        hasAxisMetadata: !!axisMetadata,
                        hasElementBboxes: !!axisMetadata?.element_bboxes,
                        elementCount: axisMetadata?.element_bboxes ? Object.keys(axisMetadata.element_bboxes).length : 0,
                        objectType: result.type
                    });
                }
            } else {
                result = await this.canvasManager.addImage(imageUrl, {
                    scaleToFit: true,
                    name: plot.display_name,
                    axisMetadata: axisMetadata,
                    csvData: finalCsvData,
                    plotInfo: { plot, category },
                });
            }

            if (result) {
                const rows = Array.isArray(result) ? 0 : (result.csvData?.length || 0);
                console.log(`[SigmaEditor] ${isSvg ? 'SVG' : 'Image'} loaded with csvData: ${!!finalCsvData}, rows: ${rows}`);
            }
            this.updateStatusBar(`Loaded: ${plot.display_name}`);
        } catch (err) {
            console.error('[SigmaEditor] Failed to load static image:', err);
            this.updateStatusBar(`Failed to load: ${plot.display_name}`);
        }
    }

    /**
     * Get manager instances for external access
     */
    public getManagers() {
        return {
            canvasManager: this.canvasManager,
            dataTableManager: this.dataTableManager,
            canvasTabManager: this.canvasTabManager,
            dataTabManager: this.dataTabManager,
        };
    }

    /**
     * Load CSV data into a dedicated tab for the figure
     */
    private loadCsvDataInTab(obj: any): void {
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
            this.dataTabManager.switchToTab(existingTabId);
            this.dataTableManager.loadFromArray(obj.csvData, true);
            return;
        }

        // Create new tab for this figure
        const category = obj.plotInfo?.category || 'default';
        const tabType = this.getTabTypeFromCategory(category);
        const tabId = this.dataTabManager.createAndSwitchToTab(
            name,
            tabType,
            category.charAt(0).toUpperCase() + category.slice(1),
            name,
            obj.csvData
        );

        // Store the mapping
        this.tabToFigureMap.set(tabId, objId);
        this.figureToTabMap.set(objId, tabId);

        // Load CSV into data table
        this.dataTableManager.loadFromArray(obj.csvData, true);
        this.updateStatusBar(`Data tab created for ${name}`);
    }

    /**
     * Load CSV data and metadata for an image from the gallery
     */
    private async loadCsvForImage(obj: any): Promise<void> {
        const name = obj.name || '';
        if (!name) {
            console.log('[SigmaEditor] No name on selected image, cannot load CSV');
            return;
        }

        console.log(`[SigmaEditor] Looking up CSV for image: "${name}"`);

        try {
            // Try to find the plot in loaded gallery contents
            const contents = this.galleryCategories?.getContents();
            if (!contents) {
                console.log('[SigmaEditor] Gallery contents not loaded yet');
                return;
            }

            console.log(`[SigmaEditor] Searching ${Object.keys(contents.categories || {}).length} categories`);

            // Search for the plot by display name across all categories
            // Try multiple matching strategies
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
                    console.log(`[SigmaEditor] Found matching plot: ${plot.name} in ${category}`);
                    // Load CSV data
                    const csvUrl = plot.csv || `/vis/api/gallery/project/${category}/${plot.name}/csv/`;
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
                        console.log(`[SigmaEditor] No CSV found for ${name}`);
                    }

                    // Load axis metadata if not already present
                    if (!obj.axisMetadata) {
                        try {
                            const metaResponse = await fetch(`/vis/api/gallery/metadata/${category}/${plot.name}/`);
                            if (metaResponse.ok) {
                                const metadata = await metaResponse.json();
                                if (metadata.success && metadata.axes_bbox_px) {
                                    obj.axisMetadata = {
                                        axes_bbox_px: metadata.axes_bbox_px,
                                        figure_size_px: metadata.figure_size_px,
                                        element_bboxes: metadata.element_bboxes  // For element-level selection
                                    };
                                    // Refresh properties panel to show metadata
                                    this.propertiesManager.showCanvasObjectProperties(obj);
                                }
                            }
                        } catch (e) {
                            console.log(`[SigmaEditor] No metadata found for ${name}`);
                        }
                    }
                    break;
                }
            }

            if (!found) {
                console.log(`[SigmaEditor] No matching plot found for "${name}"`);
            }
        } catch (error) {
            console.error('[SigmaEditor] Failed to load CSV for image:', error);
        }
    }

    /**
     * Load missing axis metadata for restored objects
     * Objects may have been saved before metadata serialization was implemented
     */
    private async loadMissingMetadata(objects: any[]): Promise<void> {
        if (!objects.length) return;

        const objectsNeedingMetadata = objects.filter(
            obj => obj.type === 'image' && !obj.axisMetadata && obj.plotInfo
        );

        if (!objectsNeedingMetadata.length) {
            console.log('[SigmaEditor] All objects have axis metadata');
            return;
        }

        console.log(`[SigmaEditor] Loading metadata for ${objectsNeedingMetadata.length} objects`);

        for (const obj of objectsNeedingMetadata) {
            try {
                const { category, plot } = obj.plotInfo;
                if (!category || !plot?.name) continue;

                const metaResponse = await fetch(`/vis/api/gallery/metadata/${category}/${plot.name}/`);
                if (metaResponse.ok) {
                    const metadata = await metaResponse.json();
                    if (metadata.success && metadata.axes_bbox_px) {
                        obj.axisMetadata = {
                            axes_bbox_px: metadata.axes_bbox_px,
                            figure_size_px: metadata.figure_size_px,
                            element_bboxes: metadata.element_bboxes  // For element-level selection
                        };
                        console.log(`[SigmaEditor] Loaded metadata for ${obj.name || plot.name}`);
                    }
                }
            } catch (e) {
                console.log(`[SigmaEditor] Failed to load metadata for ${obj.name || 'unknown'}`);
            }
        }

        // Save updated canvas with metadata
        this.canvasManager.saveCanvasContent();
    }

    /**
     * Infer csv_columns from element label when csv_columns is not available (backward compatibility)
     * Uses the currently loaded data table to find matching column names
     *
     * Handles SciTeX header naming convention:
     *   ax-row-0-col-0_trace-id-sine-wave_variable-x
     *   ax-row-0-col-0_trace-id-sine-wave_variable-y
     */
    private inferCsvColumnsFromLabel(elementName: string, elementInfo: any): { x?: { name: string, index: number }, y?: { name: string, index: number } } | null {
        const currentData = this.dataTableManager.getCurrentData();
        if (!currentData || !currentData.headers || currentData.headers.length === 0) {
            console.log('[SigmaEditor] No data table loaded for column inference');
            return null;
        }

        const headers = currentData.headers;
        const label = (elementInfo.label || '').toLowerCase();
        const traceIdx = elementInfo.trace_idx;
        const axesId = elementInfo.axes_id || '';

        // Find matching columns by trace-id pattern in SciTeX headers
        // Header format: ax-row-R-col-C_trace-id-TRACENAME_variable-{x|y}
        let xColIdx = -1;
        let yColIdx = -1;

        for (let i = 0; i < headers.length; i++) {
            const header = headers[i].toLowerCase();

            // Check if header contains the trace label (e.g., "sin" matches "sine-wave")
            // or exact label match (e.g., "sine-wave" matches "sine-wave")
            const traceIdMatch = header.match(/trace-id-([^_]+)/);
            if (traceIdMatch) {
                const traceId = traceIdMatch[1];  // e.g., "sine-wave"

                // Check for partial match: "sin" in "sine-wave" or "sine-wave" contains "sin"
                const labelMatches = traceId.includes(label) ||
                                    label.includes(traceId.replace('-', '').replace('_', '')) ||
                                    traceId.startsWith(label);

                if (labelMatches) {
                    // Determine if this is x or y variable
                    if (header.endsWith('_variable-x') || header.includes('_x_') || header.endsWith('-x')) {
                        xColIdx = i;
                    } else if (header.endsWith('_variable-y') || header.includes('_y_') || header.endsWith('-y')) {
                        yColIdx = i;
                    }
                }
            }
        }

        if (xColIdx !== -1 || yColIdx !== -1) {
            const result: { x?: { name: string, index: number }, y?: { name: string, index: number } } = {};
            if (xColIdx !== -1) {
                result.x = { name: headers[xColIdx], index: xColIdx };
            }
            if (yColIdx !== -1) {
                result.y = { name: headers[yColIdx], index: yColIdx };
            }
            console.log(`[SigmaEditor] Inferred csv_columns from SciTeX header: x=${result.x?.name}, y=${result.y?.name}`);
            return result;
        }

        // Fallback: Try to find Y column by trace_idx (legacy format)
        if (traceIdx !== undefined && traceIdx + 1 < headers.length) {
            const xCol = { name: headers[0], index: 0 };
            const yColIdx = traceIdx + 1;  // trace_0 -> column 1, trace_1 -> column 2
            const yCol = { name: headers[yColIdx], index: yColIdx };
            console.log(`[SigmaEditor] Inferred csv_columns from trace_idx ${traceIdx}: x=${xCol.name}, y=${yCol.name}`);
            return { x: xCol, y: yCol };
        }

        // Fallback: Try to match by label name (simple headers)
        for (let i = 1; i < headers.length; i++) {
            const header = headers[i].toLowerCase();
            if (label.includes(header) || header.includes(label)) {
                const xCol = { name: headers[0], index: 0 };
                const yCol = { name: headers[i], index: i };
                console.log(`[SigmaEditor] Inferred csv_columns from label match: x=${xCol.name}, y=${yCol.name}`);
                return { x: xCol, y: yCol };
            }
        }

        // Last resort: Use column index based on trace name (trace_0 -> col 1, trace_1 -> col 2)
        const traceMatch = elementName.match(/trace_(\d+)/);
        if (traceMatch) {
            const idx = parseInt(traceMatch[1]) + 1;
            if (idx < headers.length) {
                const xCol = { name: headers[0], index: 0 };
                const yCol = { name: headers[idx], index: idx };
                console.log(`[SigmaEditor] Inferred csv_columns from element name: x=${xCol.name}, y=${yCol.name}`);
                return { x: xCol, y: yCol };
            }
        }

        console.log('[SigmaEditor] Could not infer csv_columns for element:', elementName, 'label:', label);
        return null;
    }

    /**
     * Parse CSV text to 2D array
     */
    private parseCSV(csvText: string): string[][] {
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
     * Re-render a plot at a new size to maintain font proportions
     * This calls the backend to regenerate the plot at the target dimensions
     */
    private async reRenderPlotAtSize(obj: any, newWidth: number, newHeight: number): Promise<void> {
        if (!obj.plotInfo) {
            console.log('[SigmaEditor] Cannot re-render: no plotInfo on object');
            return;
        }

        const { plot, category } = obj.plotInfo;
        if (!plot || !category) {
            console.log('[SigmaEditor] Cannot re-render: missing plot or category');
            return;
        }

        console.log(`[SigmaEditor] Re-rendering plot at ${newWidth}x${newHeight}px`);
        this.updateStatusBar(`Re-rendering ${obj.name || 'plot'} at ${Math.round(newWidth)}x${Math.round(newHeight)}px...`);

        try {
            // TODO: Call backend API to regenerate plot at new size
            // This would require an endpoint like:
            // POST /vis/api/gallery/render/
            // { category, plot_name, width_px, height_px }
            //
            // For now, just update the axis metadata to reflect scaling
            if (obj.axisMetadata?.axes_bbox_px && obj.originalWidth && obj.originalHeight) {
                const scaleX = newWidth / obj.originalWidth;
                const scaleY = newHeight / obj.originalHeight;

                // Store scaled axis positions for alignment calculations
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

            // Update properties panel to show new dimensions
            this.propertiesManager.showCanvasObjectProperties(obj);
            this.updateStatusBar(`Resized: ${obj.name || 'plot'}`);

        } catch (error) {
            console.error('[SigmaEditor] Failed to re-render plot:', error);
            this.updateStatusBar(`Failed to re-render: ${obj.name || 'plot'}`);
        }
    }

    /**
     * Debug function: Place all gallery plot types on canvas in a grid
     * Useful for testing element selection and visual consistency
     */
    public async plotAllTypes(): Promise<void> {
        console.log('[SigmaEditor] Loading all plot types for debugging...');
        this.updateStatusBar('Loading all plot types...');

        try {
            // Fetch available categories
            const response = await fetch('/vis/api/gallery/available/');
            if (!response.ok) throw new Error(`API error: ${response.status}`);

            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'Failed to load categories');

            // Collect all plots from all categories
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

            console.log(`[SigmaEditor] Found ${allPlots.length} plot types to load`);

            // Grid layout parameters
            const PLOT_WIDTH = 180;
            const PLOT_HEIGHT = 140;
            const COLS = 6;
            const MARGIN = 20;
            const START_X = 50;
            const START_Y = 50;

            // Load each plot and place on canvas
            for (let i = 0; i < allPlots.length; i++) {
                const plot = allPlots[i];
                const col = i % COLS;
                const row = Math.floor(i / COLS);
                const x = START_X + col * (PLOT_WIDTH + MARGIN);
                const y = START_Y + row * (PLOT_HEIGHT + MARGIN);

                try {
                    // Fetch CSV data
                    let csvData: string[][] = [];
                    try {
                        const csvResponse = await fetch(plot.csv);
                        if (csvResponse.ok) {
                            const csvText = await csvResponse.text();
                            csvData = csvText.trim().split('\n').map(line =>
                                line.split(',').map(cell => cell.trim())
                            );
                        }
                    } catch {
                        console.warn(`[SigmaEditor] No CSV for ${plot.name}`);
                    }

                    // Fetch metadata
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
                                };
                            }
                        }
                    } catch {
                        console.warn(`[SigmaEditor] No metadata for ${plot.name}`);
                    }

                    // Load SVG for crisp rendering at any zoom level
                    // Pass metadata through options so it's attached BEFORE setActiveObject
                    // This ensures selection:created can detect axisMetadata for element selection mode
                    await this.canvasManager.addSvgFromUrl(plot.svg, {
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
                    console.error(`[SigmaEditor] Failed to load ${plot.name}:`, err);
                }
            }

            this.updateStatusBar(`Loaded ${allPlots.length} plot types`);
            console.log('[SigmaEditor] All plot types loaded');

        } catch (error) {
            console.error('[SigmaEditor] Failed to load all plot types:', error);
            this.updateStatusBar('Failed to load all plot types');
        }
    }
}
