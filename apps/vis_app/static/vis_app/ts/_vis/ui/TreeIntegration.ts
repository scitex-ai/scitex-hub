/**
 * TreeIntegration - Handles tree manager integration for hierarchical figure/axes/plots structure
 *
 * Responsibilities:
 * - Initialize and manage TreeManager
 * - Setup tree section collapse/expand
 * - Handle tree event listeners (edit, delete, add, select)
 * - Synchronize tree selection with data table and properties panel
 * - Load test tree data
 * - Manage plot data display in data table
 *
 * This module implements the 3-pane responsive sync: Tree ↔ Data ↔ Properties
 */

import { TreeManager } from '../tree-manager';
import type { Figure } from '../types';
import type { PlotDataManager } from '../PlotDataManager';
import type { PropertiesManager } from '../PropertiesManager';
import type { DataTableManager } from '../DataTableManager';

export class TreeIntegration {
    private treeManager: TreeManager | null = null;
    private currentSelectedPlotId: string | null = null;
    private currentWorkspaceMode: string = 'data';
    private dataTableManager?: DataTableManager;

    constructor(
        private statusBarCallback?: (message: string) => void,
        private handleExportPlotCSVCallback?: () => void,
        private showPlotDataTableCallback?: (plotId: string, plotLabel: string) => void,
        private clearDataTableCallback?: () => void,
        private plotDataManager?: PlotDataManager,
        private propertiesManager?: PropertiesManager | null
    ) {}

    /**
     * Set current workspace mode
     */
    public setWorkspaceMode(mode: string): void {
        this.currentWorkspaceMode = mode;
    }

    /**
     * Set properties manager reference
     */
    public setPropertiesManager(manager: PropertiesManager): void {
        this.propertiesManager = manager;
    }

    /**
     * Set plot data manager reference
     */
    public setPlotDataManager(manager: PlotDataManager): void {
        this.plotDataManager = manager;
    }

    /**
     * Set data table manager reference
     */
    public setDataTableManager(manager: DataTableManager): void {
        this.dataTableManager = manager;
    }

    /**
     * Set current selected plot ID
     */
    public setCurrentSelectedPlotId(plotId: string | null): void {
        this.currentSelectedPlotId = plotId;
    }

    /**
     * Get current selected plot ID
     */
    public getCurrentSelectedPlotId(): string | null {
        return this.currentSelectedPlotId;
    }

    /**
     * Initialize TreeManager for hierarchical figure/axes/plots structure
     */
    public initializeTreeManager(): void {
        this.treeManager = new TreeManager();
        console.log('[TreeIntegration] TreeManager initialized');

        // Load test data for demonstration
        this.loadTestTreeData();

        // Setup tree action event listeners
        this.setupTreeEventListeners();

        // Setup tree section collapse/expand
        this.setupTreeSectionToggle();
    }

    /**
     * Setup tree section collapse/expand functionality
     */
    private setupTreeSectionToggle(): void {
        const sectionHeader = document.querySelector('.tree-section-header') as HTMLElement;
        if (!sectionHeader) return;

        sectionHeader.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;

            // Don't toggle if clicking the + button
            if (target.closest('.tree-add-btn')) return;

            const section = sectionHeader.closest('.tree-section') as HTMLElement;
            const content = section?.querySelector('.tree-section-content') as HTMLElement;
            const toggle = sectionHeader.querySelector('.tree-section-toggle') as HTMLElement;

            if (!content || !toggle) return;

            // Toggle visibility
            const isExpanded = toggle.classList.contains('fa-chevron-down');

            if (isExpanded) {
                // Collapse
                toggle.classList.remove('fa-chevron-down');
                toggle.classList.add('fa-chevron-right');
                content.style.display = 'none';
            } else {
                // Expand
                toggle.classList.remove('fa-chevron-right');
                toggle.classList.add('fa-chevron-down');
                content.style.display = 'block';
            }
        });
    }

    /**
     * Setup event listeners for tree actions
     */
    private setupTreeEventListeners(): void {
        const treeContainer = document.getElementById('figures-tree');
        if (!treeContainer) return;

        // Handle edit events
        treeContainer.addEventListener('tree-item-edit', ((e: CustomEvent) => {
            const { itemType, itemId, label } = e.detail;
            console.log('[TreeIntegration] Tree edit event:', { itemType, itemId, label });
            this.handleTreeItemEdit(e.detail);
        }) as EventListener);

        // Handle delete events
        treeContainer.addEventListener('tree-item-delete', ((e: CustomEvent) => {
            const { itemType, itemId, label } = e.detail;
            console.log('[TreeIntegration] Tree delete event:', { itemType, itemId, label });
            this.handleTreeItemDelete(e.detail);
        }) as EventListener);

        // Handle add events
        treeContainer.addEventListener('tree-item-add', ((e: CustomEvent) => {
            const { parentType, parentId, addableTypes } = e.detail;
            console.log('[TreeIntegration] Tree add event:', { parentType, parentId, addableTypes });
            this.handleTreeItemAdd(e.detail);
        }) as EventListener);

        // Handle selection events (for canvas synchronization)
        treeContainer.addEventListener('tree-item-select', ((e: CustomEvent) => {
            const { itemId, label } = e.detail;
            console.log('[TreeIntegration] Tree select event:', { itemId, label });
            this.handleTreeItemSelect(e.detail);
        }) as EventListener);
    }

    /**
     * Handle tree item edit
     */
    private handleTreeItemEdit(detail: any): void {
        const { itemType, itemId, label } = detail;

        // For now, show a simple prompt (can be replaced with modal later)
        const newLabel = prompt(`Edit ${itemType} label:`, label);

        if (newLabel && newLabel !== label) {
            // Update the label in the tree
            const labelElement = detail.element.querySelector('.tree-label');
            if (labelElement) {
                // Extract the suffix (e.g., "(2 Axes)" for figures)
                const match = labelElement.textContent?.match(/^(.+?)(\s*\([^)]+\))?$/);
                const suffix = match?.[2] || '';
                labelElement.textContent = newLabel + suffix;
            }

            console.log('[TreeIntegration] Updated item label:', { itemType, itemId, oldLabel: label, newLabel });
            // TODO: Update data model when integrated
        }
    }

    /**
     * Handle tree item delete
     */
    private handleTreeItemDelete(detail: any): void {
        const { itemType, itemId, label } = detail;
        console.log('[TreeIntegration] Item deleted:', { itemType, itemId, label });
        // TODO: Remove from data model when integrated
        // TODO: Remove from canvas when integrated
    }

    /**
     * Handle tree item add
     */
    private handleTreeItemAdd(detail: any): void {
        const { parentType, parentId, addableTypes, element } = detail;

        if (addableTypes.length === 0) {
            alert('Cannot add items to this section');
            return;
        }

        // Determine what to add
        let itemTypeToAdd = addableTypes[0];
        if (addableTypes.length > 1) {
            // Show selection dialog
            const selection = prompt(
                `What would you like to add?\nOptions: ${addableTypes.join(', ')}\n\nEnter type:`,
                addableTypes[0]
            );
            if (!selection || !addableTypes.includes(selection.toLowerCase())) {
                return;
            }
            itemTypeToAdd = selection.toLowerCase();
        }

        // Get label for new item
        const newLabel = prompt(`Enter ${itemTypeToAdd} label:`, `New ${itemTypeToAdd}`);
        if (!newLabel) return;

        console.log('[TreeIntegration] Adding new item:', { itemTypeToAdd, newLabel, parentType, parentId });

        // TODO: Add to data model and rebuild tree
        alert(`Adding ${itemTypeToAdd} "${newLabel}" to ${parentType}\n\nThis will create a new ${itemTypeToAdd} when data model is integrated.`);
    }

    /**
     * Handle tree item selection (synchronize with canvas and show properties)
     * Implements 3-pane responsive sync: Tree ↔ Data ↔ Properties
     */
    private handleTreeItemSelect(detail: any): void {
        const { itemId, label, element } = detail;
        console.log('[TreeIntegration] Item selected in tree:', { itemId, label });

        // Determine node type and show appropriate properties
        if (element) {
            let elementType = '';
            let elementLabel = label;

            if (element.classList.contains('tree-plot')) {
                elementType = 'plot';
                // **Plot selected: Show plot-specific data table**
                this.showPlotDataTable(itemId, label);
                this.currentSelectedPlotId = itemId;
            } else if (element.classList.contains('tree-axis')) {
                elementType = 'axis';
                // Axis selected: Clear data table (axes don't have data)
                this.clearDataTable();
                this.currentSelectedPlotId = null;
            } else if (element.classList.contains('tree-guide')) {
                elementType = 'guide';
                // Guide selected: Clear data table
                this.clearDataTable();
                this.currentSelectedPlotId = null;
            } else if (element.classList.contains('tree-annotation')) {
                elementType = 'annotation';
                // Annotation selected: Clear data table
                this.clearDataTable();
                this.currentSelectedPlotId = null;
            } else if (element.classList.contains('tree-figure')) {
                elementType = 'figure';
                // Figure selected: Clear data table
                this.clearDataTable();
                this.currentSelectedPlotId = null;
            }

            // Show properties panel for selected element
            if (elementType && this.propertiesManager) {
                // Get element data from tree (TODO: implement proper data retrieval)
                const elementData = {
                    id: itemId,
                    label: label,
                    // Additional data will be populated from data model
                };

                this.propertiesManager.showPropertiesFor(elementType, elementLabel, elementData);
            }
        }

        // TODO: Find and select corresponding canvas object
        // TODO: Highlight in canvas

        // For now, just log the selection
        console.log('[TreeIntegration] Canvas sync: Would select canvas object with ID:', itemId);
    }

    /**
     * Show plot-specific data table when plot is selected
     */
    private showPlotDataTable(plotId: string, plotLabel: string): void {
        // Delegate to callback if provided
        if (this.showPlotDataTableCallback) {
            this.showPlotDataTableCallback(plotId, plotLabel);
            return;
        }

        // Fallback implementation (if no callback provided)
        if (!this.plotDataManager) {
            console.warn('[TreeIntegration] PlotDataManager not available');
            return;
        }

        console.log(`[TreeIntegration] Displaying data table for plot ${plotId}`);
    }

    /**
     * Clear data table when non-plot item is selected
     */
    private clearDataTable(): void {
        // Delegate to callback if provided
        if (this.clearDataTableCallback) {
            this.clearDataTableCallback();
            return;
        }

        // Fallback implementation
        console.log('[TreeIntegration] Data table cleared');
    }

    /**
     * Load test data into tree (for demonstration)
     */
    private loadTestTreeData(): void {
        if (!this.treeManager) return;

        const testData: Figure[] = [
            {
                id: 'fig1',
                label: 'Figure 1',
                axes: [
                    {
                        id: 'ax1',
                        label: 'Ax 1 - Main Plot',
                        title: 'Neural Activity Over Time',
                        xLabel: 'Time (ms)',
                        yLabel: 'Firing Rate (Hz)',
                        plots: [
                            {
                                id: 'plot1',
                                type: 'line',
                                label: 'Plot1',
                                xColumn: 'time',
                                yColumn: 'firing_rate'
                            },
                            {
                                id: 'plot2',
                                type: 'scatter',
                                label: 'Plot2',
                                xColumn: 'time',
                                yColumn: 'threshold'
                            }
                        ],
                        guides: [
                            {
                                id: 'guide1',
                                type: 'legend',
                                label: 'Legend 1',
                                plots: ['plot1', 'plot2']
                            },
                            {
                                id: 'guide2',
                                type: 'colorbar',
                                label: 'Colorbar 1',
                                plots: ['plot1']
                            }
                        ],
                        annotations: [
                            {
                                id: 'annot1',
                                type: 'text',
                                label: 'Significance',
                                content: 'p < 0.01',
                                position: { x: 100, y: 50 }
                            },
                            {
                                id: 'annot2',
                                type: 'scalebar',
                                label: 'Scale bar',
                                content: '10 μm'
                            }
                        ]
                    },
                    {
                        id: 'ax2',
                        label: 'Ax 2 - Histogram',
                        title: 'Distribution',
                        xLabel: 'Value',
                        yLabel: 'Count',
                        plots: [
                            {
                                id: 'plot3',
                                type: 'bar',
                                label: 'Plot3',
                                xColumn: 'bin',
                                yColumn: 'count'
                            }
                        ],
                        guides: [],
                        annotations: []
                    }
                ]
            }
        ];

        this.treeManager.buildTree(testData);
        console.log('[TreeIntegration] Test tree data loaded');
    }

    /**
     * Get tree manager instance
     */
    public getTreeManager(): TreeManager | null {
        return this.treeManager;
    }
}
