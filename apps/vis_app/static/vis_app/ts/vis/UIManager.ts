/**
 * UIManager - Orchestrator for UI interactions and components
 *
 * REFACTORED: Now delegates to 6 focused modules:
 * - PanelControls: Sidebar/properties panel toggling
 * - RibbonButtons: Ribbon button handlers and drag/drop
 * - Modals: Sort, filter, and help modals
 * - KeyboardShortcuts: Global keyboard shortcuts
 * - TreeIntegration: Tree manager integration and events
 * - PlotDataDisplay: Plot data table display and export
 */

import { TreeManager } from './tree-manager.ts';
import { ResizerManager } from './ResizerManager.ts';
import { PlotDataManager } from './PlotDataManager.ts';
import type { PropertiesManager } from './PropertiesManager.ts';
import type { DataTableManager } from './DataTableManager.ts';

// Import UI modules
import { PanelControls } from './ui/PanelControls.ts';
import { RibbonButtons } from './ui/RibbonButtons.ts';
import { Modals } from './ui/Modals.ts';
import { KeyboardShortcuts } from './ui/KeyboardShortcuts.ts';
import { TreeIntegration } from './ui/TreeIntegration.ts';
import { PlotDataDisplay } from './ui/PlotDataDisplay.ts';

export class UIManager {
    // Module instances
    private panelControls: PanelControls;
    private ribbonButtons: RibbonButtons;
    private keyboardShortcuts: KeyboardShortcuts;
    private treeIntegration: TreeIntegration;
    private plotDataDisplay: PlotDataDisplay;

    // Direct dependencies
    private resizerManager: ResizerManager;
    private plotDataManager: PlotDataManager;

    // References (set after construction)
    private editingCell: HTMLElement | null = null;
    private propertiesManager: PropertiesManager | null = null;
    private dataTableManager: DataTableManager | null = null;

    constructor(
        private handleFileImportCallback?: (file: File) => void,
        private loadDemoDataCallback?: () => void,
        private addColumnsCallback?: (count: number) => void,
        private addRowsCallback?: (count: number) => void,
        private copySelectionCallback?: () => void,
        private createQuickPlotCallback?: (plotType: string) => void | Promise<void>,
        private zoomInCallback?: () => void,
        private zoomOutCallback?: () => void,
        private zoomToFitCallback?: () => void,
        private toggleGridCallback?: () => void,
        private firstRowIsHeaderRef?: { value: boolean },
        private firstColIsIndexRef?: { value: boolean },
        private renderEditableDataTableCallback?: () => void,
        private statusBarCallback?: (message: string) => void,
        private deleteSelectedCallback?: () => void,
        private duplicateSelectedCallback?: () => void,
        private undoCallback?: () => void,
        private redoCallback?: () => void,
        private copyCanvasObjectCallback?: () => void,
        private pasteCanvasObjectCallback?: () => void,
        private alignCallback?: (direction: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v') => void,
        private arrangeCallback?: (action: 'front' | 'back') => void,
        private distributeCallback?: (direction: 'horizontal' | 'vertical') => void,
        private sizeCallback?: (action: 'match-size' | 'match-width' | 'match-height' | 'multiple-crop') => void,
        private groupCallback?: () => void,
        private ungroupCallback?: () => void,
        private copyViewCallback?: () => void,
        private pasteViewCallback?: () => void,
        private nudgeCallback?: (direction: 'up' | 'down' | 'left' | 'right', shift: boolean) => void,
        private selectAllCallback?: () => void,
        private alignByAxisCallback?: (direction: 'L' | 'C' | 'R' | 'T' | 'M' | 'B' | 'S') => void,
        private escapeCallback?: () => void,
        private toggleThemeCallback?: () => void,
        private canvasSizeIncreaseCallback?: () => void,
        private canvasSizeDecreaseCallback?: () => void,
        private canvasSizeResetCallback?: () => void
    ) {
        // Initialize direct dependencies
        // NOTE: ResizerManager is no longer used for sidebar/properties panels
        // Those are now handled by shared/workspace-panel-resizer.ts via data-panel-resizer attributes
        this.resizerManager = new ResizerManager();
        // this.resizerManager.initializeVisResizers();  // DISABLED: Conflicts with workspace-panel-resizer
        this.plotDataManager = new PlotDataManager();

        // Initialize PanelControls module
        this.panelControls = new PanelControls(statusBarCallback);

        // Initialize RibbonButtons module
        this.ribbonButtons = new RibbonButtons(
            handleFileImportCallback,
            loadDemoDataCallback,
            addColumnsCallback,
            addRowsCallback,
            firstRowIsHeaderRef,
            firstColIsIndexRef,
            renderEditableDataTableCallback,
            statusBarCallback,
            () => Modals.showSortModal(),
            () => Modals.showFilterModal(),
            () => Modals.showTableHelp(),
            createQuickPlotCallback,
            () => this.plotDataDisplay.handleExportPlotCSV()
        );

        // Initialize KeyboardShortcuts module
        this.keyboardShortcuts = new KeyboardShortcuts(
            createQuickPlotCallback,
            zoomInCallback,
            zoomOutCallback,
            zoomToFitCallback,
            toggleGridCallback,
            copySelectionCallback,
            (cell) => this.setEditingCell(cell),
            statusBarCallback,
            deleteSelectedCallback,
            duplicateSelectedCallback,
            undoCallback,
            redoCallback,
            copyCanvasObjectCallback,
            pasteCanvasObjectCallback,
            alignCallback,
            arrangeCallback,
            distributeCallback,
            sizeCallback,
            groupCallback,
            ungroupCallback,
            copyViewCallback,
            pasteViewCallback,
            nudgeCallback,
            selectAllCallback,
            alignByAxisCallback,
            escapeCallback,
            toggleThemeCallback,
            canvasSizeIncreaseCallback,
            canvasSizeDecreaseCallback,
            canvasSizeResetCallback
        );

        // Initialize TreeIntegration module
        this.treeIntegration = new TreeIntegration(
            statusBarCallback,
            () => this.plotDataDisplay.handleExportPlotCSV(),
            (plotId, label) => this.plotDataDisplay.showPlotDataTable(plotId, label),
            () => this.plotDataDisplay.clearDataTable()
        );

        // Set plot data manager reference in TreeIntegration
        this.treeIntegration.setPlotDataManager(this.plotDataManager);

        // Initialize PlotDataDisplay module
        this.plotDataDisplay = new PlotDataDisplay(
            this.plotDataManager,
            undefined, // DataTableManager set later via setDataTableManager
            statusBarCallback
        );
    }

    // ========================================
    // PUBLIC API - Initialization
    // ========================================

    public initializeEventListeners(): void {
        // NOTE: Sidebar and properties toggle are now handled by shared/workspace-panel-resizer.ts
        // via data-panel-resizer attributes. Disabled legacy PanelControls to prevent conflicts.
        // this.panelControls.initSidebarToggle();
        // this.panelControls.initPropertiesToggle();
        this.ribbonButtons.initRibbonButtons();
        this.ribbonButtons.initDragAndDrop();
        this.initPanelResizers();
        console.log('[UIManager] All UI event listeners initialized');
    }

    public setupKeyboardShortcuts(): void {
        this.keyboardShortcuts.setupKeyboardShortcuts();
    }

    public initializeTreeManager(): void {
        this.treeIntegration.initializeTreeManager();
        console.log('[UIManager] TreeManager initialized via TreeIntegration');
    }

    // ========================================
    // PUBLIC API - Setters
    // ========================================

    public setEditingCell(cell: HTMLElement | null): void {
        this.editingCell = cell;
        this.keyboardShortcuts.setEditingCell(cell);
    }

    public setPropertiesManager(manager: PropertiesManager): void {
        this.propertiesManager = manager;
        this.treeIntegration.setPropertiesManager(manager);
    }

    public setDataTableManager(manager: DataTableManager): void {
        this.dataTableManager = manager;
        this.plotDataDisplay.setDataTableManager(manager);
        this.treeIntegration.setDataTableManager(manager);
    }

    // ========================================
    // PUBLIC API - Getters
    // ========================================

    public getPlotDataManager(): PlotDataManager {
        return this.plotDataManager;
    }

    public getCurrentWorkspaceMode(): string {
        return this.treeIntegration.getCurrentWorkspaceMode();
    }

    public getTreeManager(): TreeManager | null {
        return this.treeIntegration.getTreeManager();
    }

    // ========================================
    // PUBLIC API - Plot Data
    // ========================================

    public syncDataTableToPlot(): void {
        this.plotDataDisplay.syncDataTableToPlot();
    }

    // ========================================
    // PUBLIC API - Status Bar
    // ========================================

    public updateStatusBar(message?: string): void {
        const statusEl = document.getElementById('status-message');
        if (!statusEl) return;

        if (!message) {
            const zoomLevel = document.getElementById('canvas-zoom')?.textContent || '100%';
            statusEl.textContent = `Zoom: ${zoomLevel} | Ready`;
            return;
        }

        // Update status bar directly (removed callback to prevent infinite recursion)
        statusEl.textContent = message;
    }

    // ========================================
    // PRIVATE - Panel Resizers (delegated to ResizerManager)
    // ========================================

    private initPanelResizers(): void {
        // NOTE: Sidebar and properties panel resizers are now handled by shared/workspace-panel-resizer.ts
        // via data-panel-resizer attributes. The ResizerManager is only used for the split resizer
        // (data-pane / canvas-pane) which doesn't have collapse functionality.
        // this.resizerManager.initializeVisResizers();  // DISABLED: Conflicts with workspace-panel-resizer
        console.log('[UIManager] Panel resizers delegated to workspace-panel-resizer via data attributes');
    }
}
