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
} from '../vis/index.js';

import { setupGraphOperations } from './graph.js';

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

    // Plot-related state
    private currentPlot: any = null;
    private currentPlotType: string = '';

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
            (message: string) => this.updateStatusBar(message)
        );

        // Initialize DataTabManager
        this.dataTabManager = new DataTabManager();
        this.dataTabManager.setCallbacks(
            (tabId: string) => {
                console.log('[SigmaEditor] Data tab changed to:', tabId);
            },
            (tabId: string) => {
                console.log('[SigmaEditor] Data tab closed:', tabId);
            },
            (tabId: string, newName: string) => {
                console.log('[SigmaEditor] Data tab renamed:', tabId, 'to', newName);
            }
        );

        // Initialize CanvasTabManager
        this.canvasTabManager = new CanvasTabManager();
        this.canvasTabManager.setCallbacks(
            (tabId: string) => {
                console.log('[SigmaEditor] Canvas tab changed to:', tabId);
                const activeTab = this.canvasTabManager.getActiveTab();
                if (activeTab) {
                    this.updateStatusBar(`Switched to ${activeTab.figureName}`);
                }
            },
            (tabId: string) => {
                console.log('[SigmaEditor] Canvas tab closed:', tabId);
            },
            (tabId: string, newName: string) => {
                console.log('[SigmaEditor] Canvas tab renamed:', tabId, 'to', newName);
            }
        );
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
        this.rulersManager['canvas'] = this.canvasManager.canvas;
        this.rulersManager.initializeRulers();
        this.rulersManager.setupRulerDragging();

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

        setTimeout(() => {
            this.canvasManager.zoomToFit();
            this.updateRulersAreaTransform();
            console.log(`[SigmaEditor] Initial zoom: ${Math.round(this.canvasManager.getCanvasZoomLevel() * 100)}%`);
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

        this.updateStatusBar('Ready');

        const phase4End = performance.now();
        console.log(`[SigmaEditor] Phase 4 complete in ${(phase4End - phase4Start).toFixed(2)}ms`);

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
     * Update rulers area transform
     */
    private updateRulersAreaTransform(): void {
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
        if (!rulersArea) return;

        const zoom = this.canvasManager.getCanvasZoomLevel();
        const pan = this.canvasManager.getCanvasPanOffset();

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
     */
    public updateCanvasTheme(isDark: boolean): void {
        this.canvasManager.updateCanvasTheme(isDark);
        this.rulersManager.updateRulerTheme(isDark);
    }

    /**
     * Initialize PlotGallery and attach to plot type buttons
     */
    private initializePlotGallery(): void {
        this.plotGallery = new PlotGallery({
            onSelect: async (plot, gallery) => {
                console.log(`[SigmaEditor] Plot selected: ${plot.name} from ${gallery.name}`);
                this.updateStatusBar(`Loading template: ${plot.name}...`);

                // Try to load the template and add to canvas
                const plotId = plot.id.split('_').slice(1).join('_');
                const thumbnailUrl = `/vis/api/gallery/${gallery.id}/${plotId}/thumbnail/?format=binary`;

                try {
                    await this.canvasManager.addImage(thumbnailUrl, {
                        scaleToFit: true,
                        name: plot.name,
                    });
                    this.updateStatusBar(`Added: ${plot.name}`);
                } catch (err) {
                    console.error('[SigmaEditor] Failed to add plot thumbnail:', err);
                    this.updateStatusBar(`Failed to add: ${plot.name}`);
                }
            }
        });

        // Attach gallery dropdowns to plot type buttons
        const plotTypeButtons = document.querySelectorAll('.pane-header-btn[data-plot-type]');
        plotTypeButtons.forEach((btn) => {
            const plotType = (btn as HTMLElement).dataset.plotType;
            if (plotType) {
                // Map button plot types to gallery categories
                const categoryMap: Record<string, string> = {
                    'scatter': 'scatter',
                    'line': 'line',
                    'bar': 'bar',
                    'histogram': 'distribution',
                    'box': 'statistical',
                    '3d': 'other',
                    'contour': 'contour',
                    'heatmap': 'heatmap',
                };
                const category = categoryMap[plotType] || 'all';
                this.plotGallery.attachToButton(btn as HTMLElement, category);
                console.log(`[SigmaEditor] Attached gallery to ${plotType} button (category: ${category})`);
            }
        });

        console.log('[SigmaEditor] PlotGallery initialized and attached to buttons');
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
}
