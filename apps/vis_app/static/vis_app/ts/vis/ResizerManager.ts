/**
 * ResizerManager - Centralized panel resizing logic
 *
 * Single-source-of-truth for all panel resize operations
 * Ensures minimum width constraints across all affected panels
 */

interface ResizerConfig {
    resizerId: string;
    targetPanel: string;      // The panel being directly resized
    affectedPanels: string[]; // All panels that must maintain minimum width
    minWidth: number;
    maxWidth: number;
    resizeTarget: 'left' | 'right';
}

export class ResizerManager {
    private resizers: Map<string, ResizerConfig> = new Map();
    private static STORAGE_KEY = 'scitex-vis-panel-sizes';

    /**
     * Register a panel resizer with its configuration
     */
    public registerResizer(config: ResizerConfig): void {
        this.resizers.set(config.resizerId, config);
        this.restorePanelSize(config);  // Restore saved size before initializing
        this.initializeResizer(config);
    }

    /**
     * Save panel size to localStorage
     */
    private savePanelSize(config: ResizerConfig, width: number): void {
        try {
            const stored = localStorage.getItem(ResizerManager.STORAGE_KEY);
            const sizes = stored ? JSON.parse(stored) : {};
            sizes[config.resizerId] = width;
            localStorage.setItem(ResizerManager.STORAGE_KEY, JSON.stringify(sizes));
        } catch (e) {
            console.warn('[ResizerManager] Failed to save panel size:', e);
        }
    }

    /**
     * Restore panel size from localStorage
     */
    private restorePanelSize(config: ResizerConfig): void {
        try {
            const stored = localStorage.getItem(ResizerManager.STORAGE_KEY);
            if (!stored) return;

            const sizes = JSON.parse(stored);
            const savedWidth = sizes[config.resizerId];

            if (savedWidth && savedWidth >= config.minWidth) {
                const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;
                if (targetPanel) {
                    targetPanel.style.width = `${savedWidth}px`;
                    targetPanel.style.flexShrink = '0';
                    targetPanel.style.flexGrow = '0';
                    console.log(`[ResizerManager] Restored ${config.resizerId} to ${savedWidth}px`);
                }
            }
        } catch (e) {
            console.warn('[ResizerManager] Failed to restore panel size:', e);
        }
    }

    /**
     * Initialize a single resizer with event handlers
     */
    private initializeResizer(config: ResizerConfig): void {
        const resizer = document.getElementById(config.resizerId);
        const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;

        if (!resizer || !targetPanel) {
            console.warn(`[ResizerManager] Failed to initialize ${config.resizerId}`);
            return;
        }

        let isResizing = false;
        let startX = 0;
        let startWidth = 0;

        const handleMouseDown = (e: MouseEvent) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = targetPanel.offsetWidth;

            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            e.preventDefault();
        };

        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing) return;

            const delta = e.clientX - startX;

            // Calculate new width based on resize direction
            const newWidth = config.resizeTarget === 'left'
                ? startWidth + delta
                : startWidth - delta;

            // Check if new width is within bounds for target panel
            if (newWidth < config.minWidth || newWidth > config.maxWidth) {
                return;
            }

            // Check all affected panels maintain minimum width
            if (!this.checkAllPanelConstraints(config, delta)) {
                return;
            }

            // Apply resize
            targetPanel.style.width = `${newWidth}px`;
            targetPanel.style.flexShrink = '0';
            targetPanel.style.flexGrow = '0';
        };

        const handleMouseUp = () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                // Save panel size to localStorage
                this.savePanelSize(config, targetPanel.offsetWidth);
            }
        };

        resizer.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        console.log(`[ResizerManager] Initialized ${config.resizerId} affecting ${config.affectedPanels.length} panels`);
    }

    /**
     * Check that all affected panels will maintain minimum width after resize
     */
    private checkAllPanelConstraints(config: ResizerConfig, delta: number): boolean {
        for (const panelSelector of config.affectedPanels) {
            const panel = document.querySelector(panelSelector) as HTMLElement;
            if (!panel) continue;

            const currentWidth = panel.offsetWidth;

            // Calculate how this panel will be affected by the resize
            let newWidth = currentWidth;

            if (panelSelector === config.targetPanel) {
                // This is the target panel
                newWidth = config.resizeTarget === 'left'
                    ? currentWidth + delta
                    : currentWidth - delta;
            } else {
                // This is an affected panel - calculate its new width
                // For flexbox layouts, when one panel grows, others shrink
                // The exact calculation depends on the layout structure

                // If target is expanding (delta > 0 for left, delta < 0 for right)
                // then other panels in the same container shrink
                const isTargetExpanding = config.resizeTarget === 'left' ? delta > 0 : delta < 0;

                if (isTargetExpanding) {
                    // Other panels shrink by delta
                    newWidth = currentWidth - Math.abs(delta);
                } else {
                    // Other panels grow by delta
                    newWidth = currentWidth + Math.abs(delta);
                }
            }

            // Check minimum constraint
            if (newWidth < config.minWidth) {
                console.log(`[ResizerManager] Blocked: ${panelSelector} would be ${newWidth}px (min: ${config.minWidth}px)`);
                return false;
            }
        }

        return true;
    }

    /**
     * Initialize all standard Vis editor panel resizers
     */
    public initializeVisResizers(): void {
        // Sidebar resizer: Project ↔ Data Table
        // Affected panels: Project, Data Table, Canvas (all must stay >= 10px)
        this.registerResizer({
            resizerId: 'sidebar-resizer',
            targetPanel: '.vis-sidebar',
            affectedPanels: ['.vis-sidebar', '#data-pane', '#canvas-pane'],
            minWidth: 10,
            maxWidth: Infinity,
            resizeTarget: 'left'
        });

        // Split resizer: Data Table ↔ Canvas
        // Affected panels: Data Table, Canvas
        this.registerResizer({
            resizerId: 'split-resizer',
            targetPanel: '#data-pane',
            affectedPanels: ['#data-pane', '#canvas-pane'],
            minWidth: 10,
            maxWidth: Infinity,
            resizeTarget: 'left'
        });

        // Workspace resizer: Workspace ↔ Properties
        // Affected panels: Workspace (including Data + Canvas), Properties
        this.registerResizer({
            resizerId: 'workspace-resizer',
            targetPanel: '.vis-properties',
            affectedPanels: ['.vis-workspace', '.vis-properties'],
            minWidth: 10,
            maxWidth: Infinity,
            resizeTarget: 'right'
        });

        console.log('[ResizerManager] All Vis editor resizers initialized');
    }
}
