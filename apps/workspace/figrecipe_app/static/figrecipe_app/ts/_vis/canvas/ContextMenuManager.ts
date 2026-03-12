/**
 * ContextMenuManager - Handles right-click context menu for canvas operations
 *
 * Responsibilities:
 * - Context menu positioning and visibility
 * - Menu item visibility based on selection state
 * - Event handling for menu actions
 * - Action routing to appropriate handlers
 *
 * Refactored: ContextMenuTemplate handles HTML and CSS generation.
 */

import { getContextMenuHTML, addContextMenuStyles } from './ContextMenuTemplate';

export class ContextMenuManager {
    private contextMenuElement: HTMLDivElement | null = null;
    private contextMenuCallbacks: {
        // Basic operations
        copy?: () => void;
        paste?: () => void;
        delete?: () => void;
        duplicate?: () => void;

        // Layer operations
        bringToFront?: () => void;
        sendToBack?: () => void;

        // Alignment
        alignObjects?: (alignment: string) => void;
        distributeObjects?: (direction: string) => void;
        matchSize?: () => void;
        matchWidth?: () => void;
        matchHeight?: () => void;

        // Axis alignment
        alignByAxis?: (direction: string) => void;
        stackVertically?: () => void;

        // Crop operations
        enterCropMode?: () => void;
        autoCropMargin?: () => void;
        resetCrop?: () => void;
        multipleCrop?: () => void;

        // Transform operations
        flipHorizontal?: () => void;
        flipVertical?: () => void;
        rotateObjects?: (degrees: number) => void;
        resetSize?: () => void;

        // Group operations
        groupObjects?: () => void;
        ungroupObjects?: () => void;

        // View operations
        copyView?: () => void;
        pasteView?: () => void;

        // Statistics
        runRecommendedStatTest?: () => void;
        runAllStatTests?: () => void;
        showStatTestSelector?: () => void;
        openStatsInspector?: () => void;

        // Export operations
        exportAsPng?: () => void;
        exportAsSvg?: () => void;
        exportAsPdf?: () => void;

        // Download operations
        downloadFigzBundle?: () => void;
        downloadPltzBundle?: () => void;

        // Canvas operations
        saveCanvas?: () => void;
        toggleTheme?: () => void;
        zoomToFit?: () => void;
        resetView?: () => void;
    } = {};

    private rightClickPanOccurred: boolean = false;

    constructor(
        private canvas: any,
        private getSelectedElementNames: () => string[],
        private statusBarCallback?: (message: string) => void
    ) {}

    /**
     * Set callbacks for context menu actions
     */
    public setCallbacks(callbacks: Partial<typeof this.contextMenuCallbacks>): void {
        this.contextMenuCallbacks = { ...this.contextMenuCallbacks, ...callbacks };
    }

    /**
     * Setup context menu on the canvas container
     */
    public setupContextMenu(container: HTMLElement): void {
        // Create context menu element
        this.contextMenuElement = document.createElement('div');
        this.contextMenuElement.id = 'canvas-context-menu';
        this.contextMenuElement.className = 'canvas-context-menu';
        this.contextMenuElement.innerHTML = getContextMenuHTML();
        this.contextMenuElement.style.cssText = `
            position: fixed;
            display: none;
            background: var(--bg-secondary, #1e1e1e);
            border: 1px solid var(--border-color, #333);
            border-radius: 6px;
            padding: 4px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            min-width: 160px;
        `;
        document.body.appendChild(this.contextMenuElement);

        // Add CSS styles for menu items
        addContextMenuStyles();

        // Setup event handlers
        this.setupEventHandlers(container);

        console.log('[ContextMenuManager] Context menu initialized');
    }

    /**
     * Mark that right-click pan occurred (suppresses menu)
     */
    public setRightClickPanOccurred(value: boolean): void {
        this.rightClickPanOccurred = value;
    }

    /**
     * Show context menu at position
     */
    private showContextMenu(x: number, y: number, activeObj: any, hasElementSelection: boolean): void {
        if (!this.contextMenuElement) return;

        const menu = this.contextMenuElement;

        // Show/hide multi-select-only options
        const multiSelectSections = menu.querySelectorAll('.multi-select-section');
        const isMultiSelect = activeObj?.type === 'activeSelection';
        multiSelectSections.forEach(section => {
            (section as HTMLElement).style.display = isMultiSelect ? 'block' : 'none';
        });

        // Show/hide image-only options (Crop)
        const imageOnlySections = menu.querySelectorAll('.image-only-section');
        const isImage = activeObj?.type === 'image' ||
            (isMultiSelect && (activeObj as any).getObjects?.()?.some((o: any) => o.type === 'image'));
        imageOnlySections.forEach(section => {
            (section as HTMLElement).style.display = isImage ? 'block' : 'none';
        });

        // Show/hide stats section
        const statsSections = menu.querySelectorAll('.stats-section');
        const hasPlotData = isMultiSelect && activeObj && (activeObj as any).getObjects?.()?.some((o: any) => o.plotData);
        statsSections.forEach(section => {
            (section as HTMLElement).style.display = (isMultiSelect || hasPlotData || hasElementSelection) ? 'block' : 'none';
        });

        // Position menu at cursor
        menu.style.left = `${x}px`;
        menu.style.top = `${y}px`;
        menu.style.display = 'block';

        // Ensure menu stays in viewport
        const rect = menu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            menu.style.left = `${window.innerWidth - rect.width - 5}px`;
        }
        if (rect.bottom > window.innerHeight) {
            menu.style.top = `${window.innerHeight - rect.height - 5}px`;
        }

        // Check if submenus need to open to the left
        const submenus = menu.querySelectorAll('.context-menu-submenu');
        const menuRight = menu.getBoundingClientRect().right;
        const submenuWidth = 140;
        submenus.forEach(submenu => {
            if (menuRight + submenuWidth > window.innerWidth) {
                submenu.classList.add('submenu-left');
            } else {
                submenu.classList.remove('submenu-left');
            }
        });
    }

    /**
     * Hide context menu
     */
    private hideContextMenu(): void {
        if (this.contextMenuElement) {
            this.contextMenuElement.style.display = 'none';
        }
    }

    /**
     * Handle context menu action
     */
    private handleAction(action: string): void {
        this.hideContextMenu();

        switch (action) {
            case 'copy':
                this.contextMenuCallbacks.copy?.();
                break;
            case 'paste':
                this.contextMenuCallbacks.paste?.();
                break;
            case 'delete':
                this.contextMenuCallbacks.delete?.();
                break;
            case 'duplicate':
                this.contextMenuCallbacks.duplicate?.();
                break;
            case 'bring-front':
                this.contextMenuCallbacks.bringToFront?.();
                break;
            case 'send-back':
                this.contextMenuCallbacks.sendToBack?.();
                break;
            case 'align-left':
                this.contextMenuCallbacks.alignObjects?.('left');
                break;
            case 'align-right':
                this.contextMenuCallbacks.alignObjects?.('right');
                break;
            case 'align-top':
                this.contextMenuCallbacks.alignObjects?.('top');
                break;
            case 'align-bottom':
                this.contextMenuCallbacks.alignObjects?.('bottom');
                break;
            case 'align-center-h':
                this.contextMenuCallbacks.alignObjects?.('center-h');
                break;
            case 'align-center-v':
                this.contextMenuCallbacks.alignObjects?.('center-v');
                break;
            case 'distribute-h':
                this.contextMenuCallbacks.distributeObjects?.('horizontal');
                break;
            case 'distribute-v':
                this.contextMenuCallbacks.distributeObjects?.('vertical');
                break;
            case 'match-size':
                this.contextMenuCallbacks.matchSize?.();
                break;
            case 'match-width':
                this.contextMenuCallbacks.matchWidth?.();
                break;
            case 'match-height':
                this.contextMenuCallbacks.matchHeight?.();
                break;
            case 'multiple-crop':
                this.contextMenuCallbacks.multipleCrop?.();
                break;
            case 'align-by-axis-l':
                this.contextMenuCallbacks.alignByAxis?.('L');
                break;
            case 'align-by-axis-c':
                this.contextMenuCallbacks.alignByAxis?.('C');
                break;
            case 'align-by-axis-r':
                this.contextMenuCallbacks.alignByAxis?.('R');
                break;
            case 'align-by-axis-t':
                this.contextMenuCallbacks.alignByAxis?.('T');
                break;
            case 'align-by-axis-m':
                this.contextMenuCallbacks.alignByAxis?.('M');
                break;
            case 'align-by-axis-b':
                this.contextMenuCallbacks.alignByAxis?.('B');
                break;
            case 'align-by-axis-s':
                this.contextMenuCallbacks.stackVertically?.();
                break;
            case 'crop-manual':
                this.contextMenuCallbacks.enterCropMode?.();
                break;
            case 'crop-margin':
                this.contextMenuCallbacks.autoCropMargin?.();
                break;
            case 'crop-reset':
                this.contextMenuCallbacks.resetCrop?.();
                break;
            case 'flip-h':
                this.contextMenuCallbacks.flipHorizontal?.();
                break;
            case 'flip-v':
                this.contextMenuCallbacks.flipVertical?.();
                break;
            case 'rotate-90':
                this.contextMenuCallbacks.rotateObjects?.(90);
                break;
            case 'rotate-180':
                this.contextMenuCallbacks.rotateObjects?.(180);
                break;
            case 'reset-size':
                this.contextMenuCallbacks.resetSize?.();
                break;
            case 'group':
                this.contextMenuCallbacks.groupObjects?.();
                break;
            case 'ungroup':
                this.contextMenuCallbacks.ungroupObjects?.();
                break;
            case 'copy-view':
                this.contextMenuCallbacks.copyView?.();
                break;
            case 'paste-view':
                this.contextMenuCallbacks.pasteView?.();
                break;
            case 'stats-recommended':
                this.contextMenuCallbacks.runRecommendedStatTest?.();
                break;
            case 'stats-all':
                this.contextMenuCallbacks.runAllStatTests?.();
                break;
            case 'stats-select':
                this.contextMenuCallbacks.showStatTestSelector?.();
                break;
            case 'stats-inspector':
                this.contextMenuCallbacks.openStatsInspector?.();
                break;
            case 'export-png':
                this.contextMenuCallbacks.exportAsPng?.();
                break;
            case 'export-svg':
                this.contextMenuCallbacks.exportAsSvg?.();
                break;
            case 'export-pdf':
                this.contextMenuCallbacks.exportAsPdf?.();
                break;
            case 'download-figz':
                this.contextMenuCallbacks.downloadFigzBundle?.();
                break;
            case 'download-pltz':
                this.contextMenuCallbacks.downloadPltzBundle?.();
                break;
            case 'save-canvas':
                this.contextMenuCallbacks.saveCanvas?.();
                if (this.statusBarCallback) {
                    this.statusBarCallback('Figure saved');
                }
                break;
            case 'toggle-theme':
                this.contextMenuCallbacks.toggleTheme?.();
                break;
            case 'zoom-fit':
                this.contextMenuCallbacks.zoomToFit?.();
                break;
            case 'reset-view':
                this.contextMenuCallbacks.resetView?.();
                break;
        }
    }

    /**
     * Setup event handlers for context menu
     */
    private setupEventHandlers(container: HTMLElement): void {
        // Right-click handler
        container.addEventListener('contextmenu', (e: MouseEvent) => {
            e.preventDefault();

            // Skip context menu if right-click was used for panning
            if (this.rightClickPanOccurred) {
                this.rightClickPanOccurred = false;
                this.hideContextMenu();
                return;
            }

            // Check if we have an active object or element-level selection
            const activeObj = this.canvas?.getActiveObject();
            const hasElementSelection = this.getSelectedElementNames().length >= 2;

            if (!activeObj && !hasElementSelection) {
                this.hideContextMenu();
                return;
            }

            this.showContextMenu(e.clientX, e.clientY, activeObj, hasElementSelection);
        });

        // Click handlers for menu items
        if (this.contextMenuElement) {
            this.contextMenuElement.addEventListener('click', (e: MouseEvent) => {
                const target = (e.target as HTMLElement).closest('.context-menu-item');
                if (!target) return;

                // Don't close menu for submenu headers
                if ((target as HTMLElement).classList.contains('submenu-header')) {
                    return;
                }

                const action = (target as HTMLElement).dataset.action;
                if (action) {
                    this.handleAction(action);
                }
            });
        }

        // Close menu on click outside
        document.addEventListener('click', (e: MouseEvent) => {
            if (this.contextMenuElement && !this.contextMenuElement.contains(e.target as Node)) {
                this.hideContextMenu();
            }
        });

        // Close menu on escape
        document.addEventListener('keydown', (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                this.hideContextMenu();
            }
        });
    }

}
