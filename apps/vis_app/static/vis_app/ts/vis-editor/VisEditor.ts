/**
 * SciTeX Vis Editor - Main Coordinator Class
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
import { EditorCallbackHandlers } from './EditorCallbackHandlers.ts';

/**
 * VisEditor - Coordinator class that manages all editor components
 */
export class VisEditor {
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
    private callbackHandlers!: EditorCallbackHandlers;

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

    // Project context for bundle-based flow
    private projectOwner: string = '';
    private projectSlug: string = '';
    private figureName: string = 'Figure1';

    constructor() {
        console.log('[VisEditor] Initializing modular Vis Editor...');

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
            () => this.canvasManager.zoomToContent(),  // Changed from zoomToFit to fit content
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
            () => this.canvasManager.exitElementSelectionMode(),  // escapeCallback
            () => this.canvasManager.toggleCanvasTheme(),  // toggleThemeCallback
            () => this.canvasManager.increaseCanvasSize(),  // canvasSizeIncreaseCallback
            () => this.canvasManager.decreaseCanvasSize(),  // canvasSizeDecreaseCallback
            () => this.canvasManager.fitCanvasToContent()  // canvasSizeResetCallback → now fits to content
        );

        // Initialize DataTabManager
        this.dataTabManager = new DataTabManager();
        this.dataTabManager.setCallbacks(
            (tabId: string) => {
                console.log('[VisEditor] Data tab changed to:', tabId);
                // Load the tab's data into the data table
                const tabData = this.dataTabManager.getTabData(tabId);
                if (tabData && Array.isArray(tabData) && tabData.length > 0) {
                    this.dataTableManager.loadFromArray(tabData, true);
                    this.updateStatusBar(`Loaded data for tab`);
                }
            },
            (tabId: string) => {
                console.log('[VisEditor] Data tab closed:', tabId);
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
                console.log('[VisEditor] Data tab renamed:', tabId, 'to', newName);
            }
        );

        // Initialize CanvasTabManager
        this.canvasTabManager = new CanvasTabManager();
        this.canvasTabManager.setCallbacks(
            async (tabId: string) => {
                console.log('[VisEditor] Canvas tab changed to:', tabId);
                // Restore canvas content for the new tab
                await this.restoreCanvasForTab(tabId);
                const activeTab = this.canvasTabManager.getActiveTab();
                if (activeTab) {
                    this.updateStatusBar(`Switched to ${activeTab.figureName}`);
                    // Sync tree to highlight the figure's file
                    if (activeTab.figurePath) {
                        this.syncTreeToFigure(activeTab.figurePath);
                    }
                }
            },
            (tabId: string) => {
                console.log('[VisEditor] Canvas tab closed:', tabId);
                // Tab data is already removed by CanvasTabManager
            },
            (tabId: string, newName: string) => {
                console.log('[VisEditor] Canvas tab renamed:', tabId, 'to', newName);
            },
            () => {
                // onBeforeTabChange: Save current canvas before switching
                this.saveCanvasForCurrentTab();
            },
            async (figureName: string, figurePath: string) => {
                // onBundleCreated: Refresh file tree when a new figz bundle is created
                console.log('[VisEditor] New figz bundle created:', figureName, figurePath);
                await this.refreshFilesTree();
                this.updateStatusBar(`Created ${figureName}`);
            }
        );

        // Initialize callback handlers
        this.callbackHandlers = new EditorCallbackHandlers({
            canvasManager: this.canvasManager,
            propertiesManager: this.propertiesManager,
            dataTableManager: this.dataTableManager,
            rulersManager: this.rulersManager,
            syncTreeToPanel: (pltzPath: string) => this.syncTreeToPanel(pltzPath),
            loadCsvDataInTab: (obj: any) => this.loadCsvDataInTab(obj),
            loadCsvForBundlePanel: (obj: any) => this.loadCsvForBundlePanel(obj),
            loadCsvForImage: (obj: any) => this.loadCsvForImage(obj),
            updateStatusBar: (message: string) => this.updateStatusBar(message),
            inferCsvColumnsFromLabel: (elementName: string, elementInfo: any) =>
                this.inferCsvColumnsFromLabel(elementName, elementInfo),
            updateRulersAreaTransform: () => this.updateRulersAreaTransform(),
            // Gallery-related dependencies
            getTabTypeFromCategory: (category: string) => this.getTabTypeFromCategory(category),
            createPltzBundleFromGallery: (plot: any, category: string, csvData: string[][]) =>
                this.createPltzBundleFromGallery(plot, category, csvData),
            getProjectContext: () => ({
                projectOwner: this.projectOwner || (window as any).projectOwner,
                projectSlug: this.projectSlug || (window as any).projectSlug,
            }),
            setCurrentPlotState: (plot: any, plotType: string, category: string, csvData: string[][]) => {
                this.currentPlot = plot;
                this.currentPlotType = plotType;
                this.currentCategory = category;
                this.currentCsvData = csvData;
            },
        });
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

        // Check if we have actual canvas content to restore
        const hasCanvasContent = tabState && tabState.canvasJson;

        if (!hasCanvasContent || !this.canvasManager.canvas) {
            // New tab or no saved state - clear canvas for fresh start
            this.canvasManager.canvas?.clear();
            this.canvasManager.canvas?.renderAll();
            // Also reset the current figz path since this is a new/empty figure
            this.canvasManager.setCurrentFigzPath(null);

            // Re-apply current theme to the cleared canvas
            const savedCanvasTheme = localStorage.getItem('canvas-theme') || localStorage.getItem('scitex-theme-preference') || 'dark';
            const isDark = savedCanvasTheme === 'dark';
            this.canvasManager.updateCanvasTheme(isDark);

            console.log(`[VisEditor] New tab or no content - canvas cleared, theme applied: ${savedCanvasTheme}`);
            return;
        }

        if (tabState.canvasJson) {
            // Also restore the figz path from the tab
            const tab = this.canvasTabManager.getTab(tabId);
            if (tab?.figurePath) {
                this.canvasManager.setCurrentFigzPath(tab.figurePath);
            }

            // Load canvas content from tab state
            return new Promise((resolve) => {
                this.canvasManager.canvas!.loadFromJSON(tabState.canvasJson, () => {
                    // Use localStorage view state (most recent user position) over tab state
                    // This ensures the user's last position is preserved across hard refresh
                    const savedViewState = localStorage.getItem('scitex-vis-viewstate');
                    if (savedViewState) {
                        try {
                            const viewState = JSON.parse(savedViewState);
                            console.log('[VisEditor] 📂 Using localStorage view state:', viewState);
                            this.canvasManager.setCanvasZoomLevel(viewState.zoom ?? 1);
                            this.canvasManager.setCanvasPanOffset(viewState.panX ?? 0, viewState.panY ?? 0);
                        } catch (e) {
                            console.warn('[VisEditor] Failed to parse localStorage view state, falling back to tab state');
                            if (tabState.viewState) {
                                console.log('[VisEditor] 📂 Using tab view state:', tabState.viewState);
                                this.canvasManager.setCanvasZoomLevel(tabState.viewState.zoom);
                                this.canvasManager.setCanvasPanOffset(tabState.viewState.panX, tabState.viewState.panY);
                            }
                        }
                    } else if (tabState.viewState) {
                        console.log('[VisEditor] 📂 Using tab view state (no localStorage):', tabState.viewState);
                        this.canvasManager.setCanvasZoomLevel(tabState.viewState.zoom);
                        this.canvasManager.setCanvasPanOffset(tabState.viewState.panX, tabState.viewState.panY);
                    }
                    this.canvasManager.canvas!.renderAll();
                    this.updateRulersAreaTransform();
                    console.log(`[VisEditor] Restored canvas for tab ${tabId}`);
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
        console.log('[VisEditor] Starting optimized initialization...');

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
        console.log(`[VisEditor] Phase 1 complete in ${(phase1End - phase1Start).toFixed(2)}ms`);

        // PHASE 2: DEFERRED
        const phase2Start = performance.now();
        await new Promise(resolve => setTimeout(resolve, 0));

        this.setupDataTableEvents();
        this.dataTableManager.setupColumnResizing();
        this.uiManager.setupKeyboardShortcuts();

        const phase2End = performance.now();
        console.log(`[VisEditor] Phase 2 complete in ${(phase2End - phase2Start).toFixed(2)}ms`);

        // PHASE 3: DEFERRED - Canvas and heavy graphics
        const phase3Start = performance.now();
        await new Promise(resolve => setTimeout(resolve, 0));

        this.canvasManager.initCanvas();
        this.canvasManager.setupCanvasEvents();

        // Wire up selection callback to update properties panel, data tab, and tree
        this.canvasManager.setSelectionCallback(this.callbackHandlers.createSelectionCallback());

        // Wire up resize callback to re-render plots at new size
        this.canvasManager.setObjectResizedCallback(async (obj: any, newWidth: number, newHeight: number) => {
            await this.reRenderPlotAtSize(obj, newWidth, newHeight);
        });

        // Wire up element selection callback to highlight CSV columns and show properties
        this.canvasManager.setElementSelectionCallback(this.callbackHandlers.createElementSelectionCallback());

        this.rulersManager['canvas'] = this.canvasManager.canvas;
        this.rulersManager.initializeRulers();

        // Set up bidirectional sync between RulersManager and CanvasManager
        this.rulersManager.setTransformCallback(this.callbackHandlers.createTransformCallback());

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
                console.log('[VisEditor] CSV loaded via drop:', data.length, 'rows');
                // TODO: Load into data table
            },
        });

        // Restore canvas content from active tab or fallback to old localStorage
        setTimeout(
            this.callbackHandlers.createCanvasRestorationCallback(
                this.canvasTabManager,
                (tabId: string) => this.restoreCanvasForTab(tabId),
                (objects: any[]) => this.loadMissingMetadata(objects),
                () => this.saveCanvasForCurrentTab()
            ),
            100
        );

        const phase3End = performance.now();
        console.log(`[VisEditor] Phase 3 complete in ${(phase3End - phase3Start).toFixed(2)}ms`);

        // PHASE 4: DEFERRED - Properties and final setup
        const phase4Start = performance.now();
        await new Promise(resolve => setTimeout(resolve, 0));

        this.propertiesManager.initPropertiesTabs();
        this.propertiesManager.setupPropertySliders();
        this.uiManager.setPropertiesManager(this.propertiesManager);
        this.uiManager.setDataTableManager(this.dataTableManager);
        this.uiManager.initializeTreeManager();

        // Wire up panel refresh callback for bundle property editing
        this.propertiesManager.setPanelRefreshCallback(async (pltzPath: string) => {
            await this.canvasManager.refreshPanelImage(pltzPath);
        });

        // Initialize PlotGallery for thumbnail dropdowns
        this.initializePlotGallery();

        // Setup property change handlers for live preview
        this.setupPropertyChangeHandlers();

        this.updateStatusBar('Ready');

        const phase4End = performance.now();
        console.log(`[VisEditor] Phase 4 complete in ${(phase4End - phase4Start).toFixed(2)}ms`);

        // Note: Canvas theme is applied in the setTimeout callback after canvas content restoration
        // to ensure it's not overwritten by saved canvas JSON

        // Listen for global theme changes to update rulers
        document.addEventListener('theme-changed', (e: CustomEvent) => {
            const isDark = e.detail?.theme === 'dark';
            this.rulersManager.updateRulerTheme(isDark);
            console.log(`[VisEditor] Global theme changed, rulers updated to ${isDark ? 'dark' : 'light'}`);
        });

        const totalEnd = performance.now();
        console.log(`[VisEditor] Total initialization: ${(totalEnd - totalStart).toFixed(2)}ms`);
    }

    /**
     * Setup data table events
     */
    private setupDataTableEvents(): void {
        console.log('[VisEditor] Data table using native scrolling');
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
        console.log('[VisEditor] Property change handlers initialized');
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
     * Sets CSS transform and syncs state to RulersManager
     */
    private updateRulersAreaTransform(): void {
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
        if (!rulersArea) return;

        const zoom = this.canvasManager.getCanvasZoomLevel();
        const pan = this.canvasManager.getCanvasPanOffset();

        // Sync state to RulersManager for ruler drawing
        this.rulersManager.setCanvasZoomLevel(zoom);
        this.rulersManager.setCanvasPanOffset(pan);

        // Set CSS transform (needed for initial setup and ruler sync)
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

        console.log(`[VisEditor] Creating ${plotType} plot...`);
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
            onPlotSelect: this.callbackHandlers.createPlotSelectCallback(this.dataTabManager),
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
                console.log(`[VisEditor] Legacy plot selected: ${plot.name} from ${gallery.name}`);
            }
        });

        console.log('[VisEditor] GalleryCategories initialized');
    }

    /**
     * Re-render current plot with updated properties
     */
    public async reRenderCurrentPlot(): Promise<void> {
        if (!this.currentPlot || !this.currentCsvData || this.currentCsvData.length < 2) {
            console.warn('[VisEditor] No current plot to re-render');
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
                // Build axis metadata from response (including hitmap for fast element picking)
                const axisMetadata = result.axes_bbox_px ? {
                    axes_bbox_px: result.axes_bbox_px,
                    figure_size_px: { width: result.width, height: result.height },
                    element_bboxes: result.element_bboxes,
                    hitmap: result.hitmap,
                    hitmap_color_map: result.hitmap_color_map
                } : undefined;

                await this.canvasManager.addImage(result.image, {
                    scaleToFit: true,
                    name: this.currentPlot.display_name,
                    axisMetadata: axisMetadata,
                });
                this.updateStatusBar(`Updated: ${this.currentPlot.display_name}`);
            } else {
                console.error('[VisEditor] Re-render failed:', result.error);
                this.updateStatusBar(`Failed to update: ${result.error || 'Unknown error'}`);
            }
        } catch (err) {
            console.error('[VisEditor] Re-render error:', err);
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
        console.log(`[VisEditor] Loading static image (${isSvg ? 'SVG' : 'PNG'}): ${imageUrl}`);

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
                        element_bboxes: metadata.element_bboxes,  // For element-level selection
                        hitmap: metadata.hitmap,
                        hitmap_color_map: metadata.hitmap_color_map
                    };
                    console.log(`[VisEditor] Loaded axis metadata for ${plot.name}:`, axisMetadata);
                    if (metadata.element_bboxes) {
                        console.log(`[VisEditor] Element bboxes available: ${Object.keys(metadata.element_bboxes).length} elements`);
                    }
                    if (metadata.hitmap) {
                        console.log(`[VisEditor] Hitmap available for fast element picking`);
                    }
                }
            }
        } catch (err) {
            console.log(`[VisEditor] No metadata available for ${plot.name}`);
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
                        console.log(`[VisEditor] Loaded CSV data from ${plot.csv}: ${finalCsvData.length} rows`);
                    }
                } catch (e) {
                    console.log(`[VisEditor] No CSV data for ${plot.name}`);
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
                    console.log(`[VisEditor] Attached metadata to SVG group:`, {
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
                console.log(`[VisEditor] ${isSvg ? 'SVG' : 'Image'} loaded with csvData: ${!!finalCsvData}, rows: ${rows}`);
            }
            this.updateStatusBar(`Loaded: ${plot.display_name}`);
        } catch (err) {
            console.error('[VisEditor] Failed to load static image:', err);
            this.updateStatusBar(`Failed to load: ${plot.display_name}`);
        }
    }

    /**
     * Create a pltz bundle from gallery selection and add as panel.
     *
     * Always uses figz/pltz bundle format:
     * - With project context: saves to proj-root/scitex/vis/figures/
     * - Without project context: saves to user's bundle directory
     *
     * @param plot - The selected plot info
     * @param category - The plot category
     * @param csvData - Optional CSV data array
     */
    private async createPltzBundleFromGallery(
        plot: any,
        category: string,
        csvData?: string[][]
    ): Promise<void> {
        console.log(`[VisEditor] createPltzBundleFromGallery called:`, {
            plotName: plot?.name,
            displayName: plot?.display_name,
            category,
            csvRows: csvData?.length || 0
        });

        const projectOwner = this.projectOwner || (window as any).projectOwner;
        const projectSlug = this.projectSlug || (window as any).projectSlug;

        console.log(`[VisEditor] Project context:`, { projectOwner, projectSlug, figureName: this.figureName });

        // Always use bundle format - no fallback to static images
        this.updateStatusBar(`Creating bundle: ${plot.display_name}...`);

        // Map plot name to plot type
        // e.g. "line_01_basic" -> "line", "scatter_02_colored" -> "scatter"
        const plotType = this.mapPlotNameToType(plot.name, category);
        console.log(`[VisEditor] Mapped plot type: "${plot.name}" + "${category}" -> "${plotType}"`);

        // Convert CSV array to CSV string if available
        let dataCsv: string | undefined;
        if (csvData && csvData.length > 1) {
            dataCsv = csvData.map(row => row.join(',')).join('\n');
            console.log(`[VisEditor] CSV data prepared: ${dataCsv.length} chars`);
        }

        try {
            console.log('[VisEditor] Calling canvasManager.addPanelFromGallery...');
            // Use CanvasManager's addPanelFromGallery method
            // Pass gallery_category and gallery_plot_name to copy from template instead of re-rendering
            const result = await this.canvasManager.addPanelFromGallery(
                plotType,
                dataCsv,
                projectOwner,
                projectSlug,
                this.figureName,
                category,      // gallery_category
                plot.name      // gallery_plot_name
            );

            if (result) {
                this.updateStatusBar(`Panel ${result.panelLabel} created: ${plot.display_name}`);
                console.log(`[VisEditor] Created pltz bundle panel: ${result.panelLabel} at ${result.bundlePath}`);

                // Refresh file tree after creating bundle
                await this.refreshFilesTree();
            } else {
                // Bundle creation returned null - show error
                console.error('[VisEditor] Bundle creation failed - result is null');
                this.updateStatusBar(`Error: Failed to create bundle for ${plot.display_name}`);
            }
        } catch (error) {
            console.error('[VisEditor] Failed to create pltz bundle:', error);
            this.updateStatusBar(`Error: ${error}`);
        }
    }

    /**
     * Map gallery plot name to plot type for bundle creation.
     *
     * Gallery plot names are like "line_01_basic", "scatter_02_colored", "plot", etc.
     * We extract the base plot type (line, scatter, bar, etc.)
     */
    private mapPlotNameToType(plotName: string, category: string): string {
        // Direct name mappings for common gallery plot names
        const directMappings: Record<string, string> = {
            'plot': 'line',           // Generic "plot" maps to line
            'stx_line': 'line',
            'stx_shaded_line': 'line',
            'stx_plot': 'line',
        };

        const lowerName = plotName.toLowerCase();
        if (directMappings[lowerName]) {
            return directMappings[lowerName];
        }

        // Try to extract from plot name parts
        const parts = lowerName.split('_');
        const plotTypes = [
            'line', 'scatter', 'bar', 'barh', 'histogram', 'hist',
            'boxplot', 'violinplot', 'heatmap', 'contour', 'pie',
            'step', 'stem', 'area', 'kde', 'ecdf'
        ];

        for (const type of plotTypes) {
            if (parts[0] === type || lowerName.includes(type)) {
                return type;
            }
        }

        // Fallback to category
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
     * Set project context for bundle-based flow.
     *
     * @param owner - Project owner username
     * @param slug - Project slug
     * @param figureName - Optional figure name (defaults to 'Figure1')
     */
    public setProjectContext(owner: string, slug: string, figureName?: string): void {
        this.projectOwner = owner;
        this.projectSlug = slug;
        if (figureName) {
            this.figureName = figureName;
        }
        console.log(`[VisEditor] Project context set: ${owner}/${slug}/${this.figureName}`);
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
     * Get canvas manager instance for external access
     */
    public getCanvasManager(): CanvasManager {
        return this.canvasManager;
    }

    /**
     * Refresh the file tree (e.g., after creating/deleting figures)
     */
    public async refreshFilesTree(): Promise<void> {
        const filesTree = (window as any).filesTree;
        if (filesTree && typeof filesTree.refresh === 'function') {
            await filesTree.refresh();
            console.log('[VisEditor] File tree refreshed');
        } else {
            console.log('[VisEditor] filesTree not available for refresh');
        }
    }

    /**
     * Validate tabs against existing files - remove stale tabs.
     * Collects figz paths from the tree and validates canvas tabs against them.
     * Also validates data tabs against remaining figure tabs.
     */
    public validateTabsAgainstFilesystem(): void {
        // Collect figz paths from the file tree
        const figzPaths = this.collectFigzPathsFromTree();

        // Validate canvas tabs (figures)
        const removedFigureTabs = this.canvasTabManager.validateAndCleanTabs(figzPaths);

        // After validating figure tabs, validate data tabs against remaining figures
        const validFigureIds = this.canvasTabManager.getTabs().map(t => t.id);
        const removedDataTabs = this.dataTabManager.validateAndCleanTabs(validFigureIds);

        if (removedFigureTabs > 0 || removedDataTabs > 0) {
            this.updateStatusBar(`Cleaned up ${removedFigureTabs} figure(s) and ${removedDataTabs} table(s)`);
        }
    }

    /**
     * Collect all figz paths from the file tree DOM
     */
    private collectFigzPathsFromTree(): string[] {
        const paths: string[] = [];
        const treeEl = document.querySelector('.wft-tree');
        if (!treeEl) return paths;

        // Find all tree items that are figz bundles
        const items = treeEl.querySelectorAll('[data-path]');
        items.forEach(item => {
            const path = (item as HTMLElement).dataset.path || '';
            if (path.endsWith('.figz') || path.endsWith('.figz.d')) {
                paths.push(path);
            }
        });

        console.log(`[VisEditor] Found ${paths.length} figz paths in tree`);
        return paths;
    }

    /**
     * Clear all tabs and reset to defaults (for project switching)
     */
    public clearAllTabs(): void {
        this.canvasTabManager.clearAllTabs();
        this.dataTabManager.clearAllTabs();
        console.log('[VisEditor] All tabs cleared');
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
            console.log('[VisEditor] No name on selected image, cannot load CSV');
            return;
        }

        console.log(`[VisEditor] Looking up CSV for image: "${name}"`);

        try {
            // Try to find the plot in loaded gallery contents
            const contents = this.galleryCategories?.getContents();
            if (!contents) {
                console.log('[VisEditor] Gallery contents not loaded yet');
                return;
            }

            console.log(`[VisEditor] Searching ${Object.keys(contents.categories || {}).length} categories`);

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
                    console.log(`[VisEditor] Found matching plot: ${plot.name} in ${category}`);
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
                        console.log(`[VisEditor] No CSV found for ${name}`);
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
                                        element_bboxes: metadata.element_bboxes,  // For element-level selection
                                        hitmap: metadata.hitmap,
                                        hitmap_color_map: metadata.hitmap_color_map
                                    };
                                    // Refresh properties panel to show metadata
                                    this.propertiesManager.showCanvasObjectProperties(obj);
                                }
                            }
                        } catch (e) {
                            console.log(`[VisEditor] No metadata found for ${name}`);
                        }
                    }
                    break;
                }
            }

            if (!found) {
                console.log(`[VisEditor] No matching plot found for "${name}"`);
            }
        } catch (error) {
            console.error('[VisEditor] Failed to load CSV for image:', error);
        }
    }

    /**
     * Load CSV data for a bundle panel and sync with data table
     */
    private async loadCsvForBundlePanel(obj: any): Promise<void> {
        const pltzPath = obj.pltzPath;
        const panelLabel = obj.panelLabel || 'Panel';

        if (!pltzPath) {
            console.log('[VisEditor] No pltzPath on bundle panel');
            return;
        }

        console.log(`[VisEditor] Loading CSV for bundle panel: ${pltzPath}`);

        try {
            const csvUrl = `/vis/api/bundles/pltz/data/?path=${encodeURIComponent(pltzPath)}`;
            const response = await fetch(csvUrl);

            if (response.ok) {
                const csvText = await response.text();
                const csvData = this.parseCSV(csvText);

                // Store CSV data on the object for later use
                obj.csvData = csvData;

                // Create or switch to tab for this panel
                const tabType = 'default';
                const tabId = this.dataTabManager.createAndSwitchToTab(
                    `Panel ${panelLabel}`,
                    tabType,
                    'Bundle',
                    panelLabel,
                    csvData
                );

                // Load into data table
                this.dataTableManager.loadFromArray(csvData, true);

                this.updateStatusBar(`Data loaded for Panel ${panelLabel} (${csvData.length} rows)`);
                console.log(`[VisEditor] Loaded CSV for bundle panel ${panelLabel}: ${csvData.length} rows`);
            } else {
                console.log(`[VisEditor] No CSV data found for bundle: ${pltzPath}`);
                this.updateStatusBar(`No data available for Panel ${panelLabel}`);
            }
        } catch (error) {
            console.error('[VisEditor] Failed to load CSV for bundle panel:', error);
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
            console.log('[VisEditor] All objects have axis metadata');
            return;
        }

        console.log(`[VisEditor] Loading metadata for ${objectsNeedingMetadata.length} objects`);

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
                            element_bboxes: metadata.element_bboxes,  // For element-level selection
                            hitmap: metadata.hitmap,
                            hitmap_color_map: metadata.hitmap_color_map
                        };
                        console.log(`[VisEditor] Loaded metadata for ${obj.name || plot.name}`);
                    }
                }
            } catch (e) {
                console.log(`[VisEditor] Failed to load metadata for ${obj.name || 'unknown'}`);
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
            console.log('[VisEditor] No data table loaded for column inference');
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
            console.log(`[VisEditor] Inferred csv_columns from SciTeX header: x=${result.x?.name}, y=${result.y?.name}`);
            return result;
        }

        // Fallback: Try to find Y column by trace_idx (legacy format)
        if (traceIdx !== undefined && traceIdx + 1 < headers.length) {
            const xCol = { name: headers[0], index: 0 };
            const yColIdx = traceIdx + 1;  // trace_0 -> column 1, trace_1 -> column 2
            const yCol = { name: headers[yColIdx], index: yColIdx };
            console.log(`[VisEditor] Inferred csv_columns from trace_idx ${traceIdx}: x=${xCol.name}, y=${yCol.name}`);
            return { x: xCol, y: yCol };
        }

        // Fallback: Try to match by label name (simple headers)
        for (let i = 1; i < headers.length; i++) {
            const header = headers[i].toLowerCase();
            if (label.includes(header) || header.includes(label)) {
                const xCol = { name: headers[0], index: 0 };
                const yCol = { name: headers[i], index: i };
                console.log(`[VisEditor] Inferred csv_columns from label match: x=${xCol.name}, y=${yCol.name}`);
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
                console.log(`[VisEditor] Inferred csv_columns from element name: x=${xCol.name}, y=${yCol.name}`);
                return { x: xCol, y: yCol };
            }
        }

        console.log('[VisEditor] Could not infer csv_columns for element:', elementName, 'label:', label);
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
            console.log('[VisEditor] Cannot re-render: no plotInfo on object');
            return;
        }

        const { plot, category } = obj.plotInfo;
        if (!plot || !category) {
            console.log('[VisEditor] Cannot re-render: missing plot or category');
            return;
        }

        console.log(`[VisEditor] Re-rendering plot at ${newWidth}x${newHeight}px`);
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
            console.error('[VisEditor] Failed to re-render plot:', error);
            this.updateStatusBar(`Failed to re-render: ${obj.name || 'plot'}`);
        }
    }

    /**
     * Debug function: Place all gallery plot types on canvas in a grid
     * Useful for testing element selection and visual consistency
     */
    public async plotAllTypes(): Promise<void> {
        console.log('[VisEditor] Loading all plot types for debugging...');
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

            console.log(`[VisEditor] Found ${allPlots.length} plot types to load`);

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
                        console.warn(`[VisEditor] No CSV for ${plot.name}`);
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
                                    hitmap: metadata.hitmap,
                                    hitmap_color_map: metadata.hitmap_color_map
                                };
                            }
                        }
                    } catch {
                        console.warn(`[VisEditor] No metadata for ${plot.name}`);
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
                    console.error(`[VisEditor] Failed to load ${plot.name}:`, err);
                }
            }

            this.updateStatusBar(`Loaded ${allPlots.length} plot types`);
            console.log('[VisEditor] All plot types loaded');

        } catch (error) {
            console.error('[VisEditor] Failed to load all plot types:', error);
            this.updateStatusBar('Failed to load all plot types');
        }
    }

    /**
     * Sync tree selection to highlight the panel's pltz.d file
     * Called when a bundle panel is selected on canvas
     */
    private syncTreeToPanel(absolutePltzPath: string): void {
        this.syncTreeToPath(absolutePltzPath, 'panel');
    }

    /**
     * Sync tree selection to highlight the figure's figz.d file
     * Called when a figure tab is switched
     */
    private syncTreeToFigure(absoluteFigzPath: string): void {
        this.syncTreeToPath(absoluteFigzPath, 'figure');
    }

    /**
     * Sync tree selection to a given absolute path
     */
    private syncTreeToPath(absolutePath: string, source: string): void {
        if (!this.projectOwner || !this.projectSlug) {
            console.log(`[VisEditor] No project context, skipping tree sync (${source})`);
            return;
        }

        // Convert absolute path to relative path for tree
        // /app/data/users/{owner}/proj/{slug}/{relativePath} → {relativePath}
        const prefix = `/app/data/users/${this.projectOwner}/proj/${this.projectSlug}/`;
        let relativePath = absolutePath;
        if (absolutePath.startsWith(prefix)) {
            relativePath = absolutePath.substring(prefix.length);
        }

        // Use the globally exposed filesTree
        const filesTree = (window as any).filesTree;
        if (filesTree && typeof filesTree.selectFile === 'function') {
            // Use skipCallback=true to avoid re-triggering file selection events
            filesTree.selectFile(relativePath, true);
            console.log(`[VisEditor] Tree synced to ${source}: ${relativePath}`);
        } else {
            console.log(`[VisEditor] filesTree not available for sync (${source})`);
        }
    }
}
