/**
 * Scholar Panel Resizer
 * Handles resizable panels for the three-column scholar workspace
 */

console.log('[DEBUG] apps/scholar_app/static/scholar_app/ts/shared/panel-resizer.ts loaded');

interface ResizerConfig {
    resizerId: string;
    targetPanel: string;
    minWidth: number;
    storageKey: string;
    resizeDirection: 'left' | 'right';  // 'left' = target panel is on left, 'right' = target panel is on right
}

class ScholarPanelResizer {
    private static STORAGE_PREFIX = 'scitex-scholar-panel-';
    private resizers: Map<string, ResizerConfig> = new Map();

    /**
     * Initialize a panel resizer
     */
    public initResizer(config: ResizerConfig): void {
        const resizer = document.getElementById(config.resizerId);
        const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;

        if (!resizer || !targetPanel) {
            console.warn(`[ScholarPanelResizer] Missing elements for ${config.resizerId}`);
            return;
        }

        this.resizers.set(config.resizerId, config);

        // Restore saved width
        this.restoreWidth(config, targetPanel);

        let isResizing = false;
        let startX = 0;
        let startWidth = 0;

        const handleMouseDown = (e: MouseEvent) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = targetPanel.offsetWidth;

            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            resizer.classList.add('active');

            e.preventDefault();
        };

        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing) return;

            const delta = e.clientX - startX;

            // Calculate new width based on resize direction
            // 'left': target panel is on left of resizer, grows when dragging right (+ delta)
            // 'right': target panel is on right of resizer, grows when dragging left (- delta)
            const newWidth = config.resizeDirection === 'left'
                ? startWidth + delta
                : startWidth - delta;

            // Enforce minimum width
            if (newWidth < config.minWidth) return;

            // Apply new width
            targetPanel.style.width = `${newWidth}px`;
            targetPanel.style.flexShrink = '0';
            targetPanel.style.flexGrow = '0';
        };

        const handleMouseUp = () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                resizer.classList.remove('active');

                // Save width
                this.saveWidth(config, targetPanel.offsetWidth);
            }
        };

        resizer.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        console.log(`[ScholarPanelResizer] Initialized ${config.resizerId} (direction: ${config.resizeDirection})`);
    }

    /**
     * Save panel width to localStorage
     */
    private saveWidth(config: ResizerConfig, width: number): void {
        try {
            localStorage.setItem(
                ScholarPanelResizer.STORAGE_PREFIX + config.storageKey,
                width.toString()
            );
        } catch (e) {
            console.warn('[ScholarPanelResizer] Failed to save width:', e);
        }
    }

    /**
     * Restore panel width from localStorage
     */
    private restoreWidth(config: ResizerConfig, panel: HTMLElement): void {
        try {
            const savedWidth = localStorage.getItem(
                ScholarPanelResizer.STORAGE_PREFIX + config.storageKey
            );
            if (savedWidth) {
                const width = parseInt(savedWidth, 10);
                if (width >= config.minWidth) {
                    panel.style.width = `${width}px`;
                    panel.style.flexShrink = '0';
                    panel.style.flexGrow = '0';
                    console.log(`[ScholarPanelResizer] Restored ${config.storageKey} to ${width}px`);
                }
            }
        } catch (e) {
            console.warn('[ScholarPanelResizer] Failed to restore width:', e);
        }
    }

    /**
     * Initialize all scholar workspace resizers
     */
    public initializeAll(): void {
        // Sidebar resizer (Files panel ↔ Main content)
        // Target: left sidebar, grows when dragging right
        this.initResizer({
            resizerId: 'sidebar-resizer',
            targetPanel: '.scholar-sidebar',
            minWidth: 40,
            storageKey: 'sidebar-width',
            resizeDirection: 'left'
        });

        // Main resizer (Main content ↔ Properties panel)
        // Target: right properties panel, grows when dragging left
        this.initResizer({
            resizerId: 'main-resizer',
            targetPanel: '.scholar-properties',
            minWidth: 40,
            storageKey: 'properties-width',
            resizeDirection: 'right'
        });

        console.log('[ScholarPanelResizer] All resizers initialized');
    }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const resizer = new ScholarPanelResizer();
    resizer.initializeAll();
});

// Export for module usage
export { ScholarPanelResizer };
