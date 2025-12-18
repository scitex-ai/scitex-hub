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
} from '../vis/index.ts';

import { setupGraphOperations } from './graph.ts';
import { EditorCallbackHandlers } from './EditorCallbackHandlers.ts';
import {
    CsvDataCoordinator,
    GalleryCoordinator,
    TabStateCoordinator,
    TreeSyncCoordinator,
} from './coordinators/index.ts';

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

    // Coordinators
    private csvDataCoordinator!: CsvDataCoordinator;
    private galleryCoordinator!: GalleryCoordinator;
    private tabStateCoordinator!: TabStateCoordinator;
    private treeSyncCoordinator!: TreeSyncCoordinator;

    // SciTeX integration
    private figureDropHandler!: FigureDropHandler;
    private scitexEditor!: SciTeXEditor;
    private callbackHandlers!: EditorCallbackHandlers;

    // Deletion flag to prevent recursive deletion
    private isDeleting: boolean = false;

    // Shared references for managers
    private firstRowIsHeader: boolean = true;
    private firstColIsIndex: boolean = false;

    // Project context for bundle-based flow
    private projectOwner: string = '';
    private projectSlug: string = '';
    private figureName: string = 'Figure1';

    constructor() {
        console.log('[VisEditor] Initializing modular Vis Editor...');
        this.initializeManagers();
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
            () => this.canvasManager.zoomToContent(),
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
            () => this.canvasManager.exitElementSelectionMode(),
            () => this.canvasManager.toggleCanvasTheme(),
            () => this.canvasManager.increaseCanvasSize(),
            () => this.canvasManager.decreaseCanvasSize(),
            () => this.canvasManager.fitCanvasToContent()
        );

        // Initialize DataTabManager
        this.dataTabManager = new DataTabManager();
        this.dataTabManager.setCallbacks(
            (tabId: string) => {
                console.log('[VisEditor] Data tab changed to:', tabId);
                const tabData = this.dataTabManager.getTabData(tabId);
                if (tabData && Array.isArray(tabData) && tabData.length > 0) {
                    this.dataTableManager.loadFromArray(tabData, true);
                    this.updateStatusBar(`Loaded data for tab`);
                }
            },
            (tabId: string) => {
                console.log('[VisEditor] Data tab closed:', tabId);
                if (!this.isDeleting) {
                    const figureId = this.csvDataCoordinator.getTabToFigureMap().get(tabId);
                    if (figureId) {
                        this.isDeleting = true;
                        this.removeFigureById(figureId);
                        this.csvDataCoordinator.getTabToFigureMap().delete(tabId);
                        this.csvDataCoordinator.getFigureToTabMap().delete(figureId);
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
                await this.restoreCanvasForTab(tabId);
                const activeTab = this.canvasTabManager.getActiveTab();
                if (activeTab) {
                    this.updateStatusBar(`Switched to ${activeTab.figureName}`);
                    if (activeTab.figurePath) {
                        this.syncTreeToFigure(activeTab.figurePath);
                    }
                }
            },
            (tabId: string) => {
                console.log('[VisEditor] Canvas tab closed:', tabId);
            },
            (tabId: string, newName: string) => {
                console.log('[VisEditor] Canvas tab renamed:', tabId, 'to', newName);
            },
            () => {
                this.saveCanvasForCurrentTab();
            },
            async (figureName: string, figurePath: string) => {
                console.log('[VisEditor] New figz bundle created:', figureName, figurePath);
                await this.refreshFilesTree();
                this.updateStatusBar(`Created ${figureName}`);
            }
        );

        // Initialize TreeSyncCoordinator (no dependencies on other coordinators)
        this.treeSyncCoordinator = new TreeSyncCoordinator({
            getProjectContext: () => ({
                projectOwner: this.projectOwner || (window as any).projectOwner,
                projectSlug: this.projectSlug || (window as any).projectSlug,
            }),
        });

        // Initialize TabStateCoordinator
        this.tabStateCoordinator = new TabStateCoordinator({
            canvasManager: this.canvasManager,
            canvasTabManager: this.canvasTabManager,
            dataTabManager: this.dataTabManager,
            rulersManager: this.rulersManager,
            updateStatusBar: (message: string) => this.updateStatusBar(message),
            updateRulersAreaTransform: () => this.updateRulersAreaTransform(),
        });

        // Initialize CsvDataCoordinator
        this.csvDataCoordinator = new CsvDataCoordinator({
            dataTabManager: this.dataTabManager,
            dataTableManager: this.dataTableManager,
            propertiesManager: this.propertiesManager,
            canvasManager: this.canvasManager,
            galleryCategories: () => this.galleryCoordinator?.getGalleryCategories() || null,
            updateStatusBar: (message: string) => this.updateStatusBar(message),
            getTabTypeFromCategory: (category: string) => this.tabStateCoordinator.getTabTypeFromCategory(category),
        });

        // Initialize callback handlers
        this.callbackHandlers = new EditorCallbackHandlers({
            canvasManager: this.canvasManager,
            propertiesManager: this.propertiesManager,
            dataTableManager: this.dataTableManager,
            rulersManager: this.rulersManager,
            syncTreeToPanel: (pltzPath: string) => this.treeSyncCoordinator.syncTreeToPanel(pltzPath),
            loadCsvDataInTab: (obj: any) => this.csvDataCoordinator.loadCsvDataInTab(obj),
            loadCsvForBundlePanel: (obj: any) => this.csvDataCoordinator.loadCsvForBundlePanel(obj),
            loadCsvForImage: (obj: any) => this.csvDataCoordinator.loadCsvForImage(obj),
            updateStatusBar: (message: string) => this.updateStatusBar(message),
            inferCsvColumnsFromLabel: (elementName: string, elementInfo: any) =>
                this.csvDataCoordinator.inferCsvColumnsFromLabel(elementName, elementInfo),
            updateRulersAreaTransform: () => this.updateRulersAreaTransform(),
            getTabTypeFromCategory: (category: string) => this.tabStateCoordinator.getTabTypeFromCategory(category),
            createPltzBundleFromGallery: (plot: any, category: string, csvData: string[][]) =>
                this.galleryCoordinator.createPltzBundleFromGallery(plot, category, csvData),
            getProjectContext: () => ({
                projectOwner: this.projectOwner || (window as any).projectOwner,
                projectSlug: this.projectSlug || (window as any).projectSlug,
            }),
            setCurrentPlotState: (plot: any, plotType: string, category: string, csvData: string[][]) => {
                this.galleryCoordinator.setPlotState(plot, plotType, category, csvData);
            },
        });

        // Initialize GalleryCoordinator (needs callbackHandlers)
        this.galleryCoordinator = new GalleryCoordinator({
            canvasManager: this.canvasManager,
            dataTableManager: this.dataTableManager,
            propertiesManager: this.propertiesManager,
            dataTabManager: this.dataTabManager,
            csvDataCoordinator: this.csvDataCoordinator,
            callbackHandlers: this.callbackHandlers,
            updateStatusBar: (message: string) => this.updateStatusBar(message),
            getProjectContext: () => ({
                projectOwner: this.projectOwner || (window as any).projectOwner,
                projectSlug: this.projectSlug || (window as any).projectSlug,
                figureName: this.figureName,
            }),
            refreshFilesTree: () => this.treeSyncCoordinator.refreshFilesTree(),
        });
    }

    /**
     * Save current canvas state to the active tab
     */
    private saveCanvasForCurrentTab(): void {
        this.tabStateCoordinator.saveCanvasForCurrentTab();
    }

    /**
     * Restore canvas content from a specific tab
     */
    private async restoreCanvasForTab(tabId: string): Promise<void> {
        return this.tabStateCoordinator.restoreCanvasForTab(tabId);
    }

    /**
     * Initialize editor components
     */
    private async initializeEditor(): Promise<void> {
        const totalStart = performance.now();
        console.log('[VisEditor] Starting optimized initialization...');

        // PHASE 1: CRITICAL PATH
        this.uiManager.initializeEventListeners();
        this.dataTabManager.initializeEventListeners();
        this.dataTabManager.renderTabs();
        // Tabs are now derived from filesystem via validateTabsAgainstFilesystem()
        // which is called when the files tree loads (see files-tree.ts)
        this.canvasTabManager.initializeEventListeners();
        this.canvasTabManager.renderTabs();
        this.dataTableManager.initializeBlankTable();

        // PHASE 2: DEFERRED
        await new Promise(resolve => setTimeout(resolve, 0));
        this.setupDataTableEvents();
        this.dataTableManager.setupColumnResizing();
        this.uiManager.setupKeyboardShortcuts();

        // PHASE 3: Canvas and heavy graphics
        await new Promise(resolve => setTimeout(resolve, 0));
        this.canvasManager.initCanvas();
        this.canvasManager.setupCanvasEvents();
        this.canvasManager.setSelectionCallback(this.callbackHandlers.createSelectionCallback());
        this.canvasManager.setObjectResizedCallback(async (obj: any, newWidth: number, newHeight: number) => {
            await this.reRenderPlotAtSize(obj, newWidth, newHeight);
        });
        this.canvasManager.setElementSelectionCallback(this.callbackHandlers.createElementSelectionCallback());

        this.rulersManager['canvas'] = this.canvasManager.canvas;
        this.rulersManager.initializeRulers();
        this.rulersManager.setTransformCallback(this.callbackHandlers.createTransformCallback());
        this.rulersManager.setupRulerDragging();
        this.updateRulersAreaTransform();

        this.figureDropHandler = new FigureDropHandler({
            canvasSelector: '#canvas-container',
            dataTableSelector: '.data-table-container',
            canvasManager: this.canvasManager,
            onCsvLoad: (data: string[][]) => {
                console.log('[VisEditor] CSV loaded via drop:', data.length, 'rows');
            },
        });

        setTimeout(
            this.callbackHandlers.createCanvasRestorationCallback(
                this.canvasTabManager,
                (tabId: string) => this.restoreCanvasForTab(tabId),
                (objects: any[]) => this.csvDataCoordinator.loadMissingMetadata(objects),
                () => this.saveCanvasForCurrentTab()
            ),
            100
        );

        // PHASE 4: Properties and final setup
        await new Promise(resolve => setTimeout(resolve, 0));
        this.propertiesManager.initPropertiesTabs();
        this.propertiesManager.setupPropertySliders();
        this.uiManager.setPropertiesManager(this.propertiesManager);
        this.uiManager.setDataTableManager(this.dataTableManager);
        this.uiManager.initializeTreeManager();

        this.propertiesManager.setPanelRefreshCallback(async (pltzPath: string) => {
            await this.canvasManager.refreshPanelImage(pltzPath);
        });

        this.initializePlotGallery();
        this.setupPropertyChangeHandlers();
        this.updateStatusBar('Ready');

        document.addEventListener('theme-changed', (e: CustomEvent) => {
            const isDark = e.detail?.theme === 'dark';
            this.rulersManager.updateRulerTheme(isDark);
        });

        const totalEnd = performance.now();
        console.log(`[VisEditor] Total initialization: ${(totalEnd - totalStart).toFixed(2)}ms`);
    }

    private setupDataTableEvents(): void {
        console.log('[VisEditor] Data table using native scrolling');
    }

    private setupPropertyChangeHandlers(): void {
        const dynamicPropsEl = document.getElementById('dynamic-properties');
        if (!dynamicPropsEl) return;

        let reRenderTimeout: ReturnType<typeof setTimeout> | null = null;
        const debounceReRender = () => {
            if (reRenderTimeout) clearTimeout(reRenderTimeout);
            reRenderTimeout = setTimeout(() => {
                this.reRenderCurrentPlot();
            }, 500);
        };

        const observer = new MutationObserver(() => {
            this.setupPropertyInputHandlers(debounceReRender);
        });

        observer.observe(dynamicPropsEl, { childList: true, subtree: true });
        this.setupPropertyInputHandlers(debounceReRender);
    }

    private setupPropertyInputHandlers(onChange: () => void): void {
        const propsContainer = document.getElementById('dynamic-properties');
        if (!propsContainer) return;

        propsContainer.querySelectorAll('input[type="range"]').forEach(slider => {
            if ((slider as any)._hasChangeHandler) return;
            slider.addEventListener('change', onChange);
            (slider as any)._hasChangeHandler = true;
        });

        propsContainer.querySelectorAll('input[type="color"]').forEach(picker => {
            if ((picker as any)._hasChangeHandler) return;
            picker.addEventListener('change', onChange);
            (picker as any)._hasChangeHandler = true;
        });

        propsContainer.querySelectorAll('select').forEach(select => {
            if ((select as any)._hasChangeHandler) return;
            select.addEventListener('change', onChange);
            (select as any)._hasChangeHandler = true;
        });

        propsContainer.querySelectorAll('input[type="text"], input[type="number"]').forEach(input => {
            if ((input as any)._hasChangeHandler) return;
            input.addEventListener('change', onChange);
            (input as any)._hasChangeHandler = true;
        });
    }

    private updateRulersAreaTransform(): void {
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
        if (!rulersArea) return;

        const zoom = this.canvasManager.getCanvasZoomLevel();
        const pan = this.canvasManager.getCanvasPanOffset();

        this.rulersManager.setCanvasZoomLevel(zoom);
        this.rulersManager.setCanvasPanOffset(pan);

        rulersArea.style.transform = `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`;
        rulersArea.style.transformOrigin = '0 0';
    }

    private updateStatusBar(message?: string): void {
        this.uiManager.updateStatusBar(message);
    }

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

        const plot = graphOps.renderPlot(plotType);
        this.galleryCoordinator.setPlotState(plot, plotType, '', []);
    }

    public updateCanvasTheme(isDark: boolean): void {
        this.canvasManager.updateCanvasTheme(isDark);
    }

    public updateGlobalTheme(isDark: boolean): void {
        this.rulersManager.updateRulerTheme(isDark);
    }

    public deleteSelectedObject(): void {
        this.isDeleting = true;

        const activeObj = this.canvasManager.canvas?.getActiveObject();
        if (activeObj) {
            const objects = activeObj.type === 'activeSelection'
                ? (activeObj as any).getObjects()
                : [activeObj];

            for (const obj of objects) {
                const objId = obj.id;
                if (objId) {
                    const tabId = this.csvDataCoordinator.getFigureToTabMap().get(objId);
                    if (tabId) {
                        this.dataTabManager.closeTab(tabId);
                        this.csvDataCoordinator.getFigureToTabMap().delete(objId);
                        this.csvDataCoordinator.getTabToFigureMap().delete(tabId);
                    }
                }
            }
        }

        this.canvasManager.removeActiveObject();
        this.canvasManager.saveCanvasContent();
        this.isDeleting = false;
        this.updateStatusBar('Object deleted');
    }

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

    public duplicateSelectedObject(): void {
        this.canvasManager.duplicateActiveObject();
    }

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

    private initializePlotGallery(): void {
        this.galleryCoordinator.initialize();
    }

    public async reRenderCurrentPlot(): Promise<void> {
        return this.galleryCoordinator.reRenderCurrentPlot();
    }

    public setProjectContext(owner: string, slug: string, figureName?: string): void {
        this.projectOwner = owner;
        this.projectSlug = slug;
        if (figureName) this.figureName = figureName;
        console.log(`[VisEditor] Project context set: ${owner}/${slug}/${this.figureName}`);
    }

    public getManagers() {
        return {
            canvasManager: this.canvasManager,
            dataTableManager: this.dataTableManager,
            canvasTabManager: this.canvasTabManager,
            dataTabManager: this.dataTabManager,
        };
    }

    public getCanvasManager(): CanvasManager {
        return this.canvasManager;
    }

    public async refreshFilesTree(): Promise<void> {
        return this.treeSyncCoordinator.refreshFilesTree();
    }

    public validateTabsAgainstFilesystem(): void {
        this.tabStateCoordinator.validateTabsAgainstFilesystem();
    }

    public clearAllTabs(): void {
        this.tabStateCoordinator.clearAllTabs();
    }

    private async reRenderPlotAtSize(obj: any, newWidth: number, newHeight: number): Promise<void> {
        return this.galleryCoordinator.reRenderPlotAtSize(obj, newWidth, newHeight);
    }

    public async plotAllTypes(): Promise<void> {
        return this.galleryCoordinator.plotAllTypes();
    }

    private syncTreeToFigure(absoluteFigzPath: string): void {
        this.treeSyncCoordinator.syncTreeToFigure(absoluteFigzPath);
    }
}
