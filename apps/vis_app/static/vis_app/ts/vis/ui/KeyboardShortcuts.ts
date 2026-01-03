/**
 * KeyboardShortcuts - Handles all keyboard shortcuts for the visualization editor
 *
 * Responsibilities:
 * - Setup keyboard event listeners
 * - Handle zoom shortcuts (+ - 0)
 * - Handle grid toggle (G or Space)
 * - Handle copy selection (Ctrl+C)
 * - Handle undo/redo (Ctrl+Z, Ctrl+Y)
 * - Handle delete operations
 * - Detect when user is editing a cell to avoid shortcut interference
 *
 * Refactored: KeyboardModeHandlers handles mode-based shortcuts.
 */

import { KeyboardModeHandlers } from './KeyboardModeHandlers';

export class KeyboardShortcuts {
    private editingCell: HTMLElement | null = null;
    private modeHandlers: KeyboardModeHandlers;

    constructor(
        private createQuickPlotCallback?: (plotType: string) => void | Promise<void>,
        private zoomInCallback?: () => void,
        private zoomOutCallback?: () => void,
        private zoomToFitCallback?: () => void,
        private toggleGridCallback?: () => void,
        private copySelectionCallback?: () => void,
        private setEditingCellRef?: (cell: HTMLElement | null) => void,
        private updateStatusBarCallback?: (message: string) => void,
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
        // Initialize mode handlers with relevant callbacks
        this.modeHandlers = new KeyboardModeHandlers({
            alignCallback: this.alignCallback,
            arrangeCallback: this.arrangeCallback,
            distributeCallback: this.distributeCallback,
            sizeCallback: this.sizeCallback,
            alignByAxisCallback: this.alignByAxisCallback,
            toggleThemeCallback: this.toggleThemeCallback,
            updateStatusBarCallback: this.updateStatusBarCallback
        });
    }

    /**
     * Set editing cell reference (for keyboard shortcut detection)
     */
    public setEditingCell(cell: HTMLElement | null): void {
        this.editingCell = cell;
        if (this.setEditingCellRef) {
            this.setEditingCellRef(cell);
        }
    }

    /**
     * Check if focus is within the canvas area
     */
    private isCanvasFocused(): boolean {
        const activeElement = document.activeElement;
        const canvasPane = document.querySelector('.canvas-pane');
        const canvasContainer = document.getElementById('canvas-container');
        const rulersArea = document.getElementById('rulers-area');
        const visRulersArea = document.querySelector('.vis-rulers-area');

        return !!(
            canvasPane?.contains(activeElement) ||
            canvasContainer?.contains(activeElement) ||
            rulersArea?.contains(activeElement) ||
            visRulersArea?.contains(activeElement) ||
            activeElement?.closest('.canvas-pane') !== null ||
            activeElement?.closest('#canvas-container') !== null ||
            activeElement?.closest('.vis-rulers-area') !== null ||
            // Also check if body is focused (click on canvas area)
            (activeElement === document.body && this.isMouseOverCanvas())
        );
    }

    /**
     * Check if mouse is currently over canvas area
     */
    private isMouseOverCanvas(): boolean {
        // Check via last known mouse position or hover state
        const canvasPane = document.querySelector('.canvas-pane:hover');
        const rulersArea = document.querySelector('.vis-rulers-area:hover');
        return !!(canvasPane || rulersArea);
    }

    /**
     * Setup keyboard shortcuts
     */
    public setupKeyboardShortcuts(): void {
        // Use capture phase to intercept Ctrl+/- before browser zoom
        window.addEventListener('keydown', (e: KeyboardEvent) => {
            // Intercept Ctrl++/- for canvas size (prevent browser zoom)
            // ONLY when focus is in canvas area
            if ((e.ctrlKey || e.metaKey) && (e.key === '+' || e.key === '=' || e.key === '-' || e.key === '_' || e.key === '0')) {
                // Skip if in input/textarea
                if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') {
                    return; // Let browser handle it
                }

                // Only intercept when canvas area has focus
                if (!this.isCanvasFocused()) {
                    console.log(`[KeyboardShortcuts] Ctrl+${e.key} ignored - canvas not focused`);
                    return; // Let browser handle it (global zoom)
                }

                e.preventDefault();
                e.stopPropagation();
                console.log(`[KeyboardShortcuts] Intercepted Ctrl+${e.key} for canvas size`);

                if (e.key === '+' || e.key === '=') {
                    if (this.canvasSizeIncreaseCallback) {
                        this.canvasSizeIncreaseCallback();
                    }
                } else if (e.key === '-' || e.key === '_') {
                    if (this.canvasSizeDecreaseCallback) {
                        this.canvasSizeDecreaseCallback();
                    }
                } else if (e.key === '0') {
                    if (this.canvasSizeResetCallback) {
                        this.canvasSizeResetCallback();
                    }
                }
                return;
            }
        }, true);  // capture: true to intercept before browser

        document.addEventListener('keydown', (e: KeyboardEvent) => {
            // Prevent shortcuts when typing in inputs
            if (document.activeElement?.tagName === 'INPUT' ||
                document.activeElement?.tagName === 'TEXTAREA' ||
                this.editingCell) {
                return;
            }

            // Alt+Shift+A - Enter Align by Axis mode (prefix for L/R/T/B/C/M/S)
            if (e.altKey && e.shiftKey && e.key.toLowerCase() === 'a' && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                this.modeHandlers.enterAlignByAxisMode();
                return;
            }

            // Ctrl+A - Select All
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && !e.altKey) {
                e.preventDefault();
                if (this.selectAllCallback) {
                    this.selectAllCallback();
                }
                return;
            }

            // Ctrl+Z - Undo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                if (this.undoCallback) {
                    this.undoCallback();
                }
            }

            // Ctrl+Y or Ctrl+Shift+Z - Redo
            if (((e.ctrlKey || e.metaKey) && e.key === 'y') ||
                ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z')) {
                e.preventDefault();
                if (this.redoCallback) {
                    this.redoCallback();
                }
            }

            // Ctrl+Shift+C - Copy View (axis limits, crop)
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'c') {
                e.preventDefault();
                if (this.copyViewCallback) {
                    this.copyViewCallback();
                }
                return;
            }

            // Ctrl+Shift+V - Paste View (axis limits, crop)
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'v') {
                e.preventDefault();
                if (this.pasteViewCallback) {
                    this.pasteViewCallback();
                }
                return;
            }

            // Ctrl+C - Copy (canvas object or table selection)
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'c' && !e.shiftKey) {
                e.preventDefault();
                // Try canvas copy first, then table copy
                if (this.copyCanvasObjectCallback) {
                    this.copyCanvasObjectCallback();
                } else if (this.copySelectionCallback) {
                    this.copySelectionCallback();
                }
            }

            // Ctrl+V - Paste canvas object
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'v' && !e.shiftKey) {
                e.preventDefault();
                if (this.pasteCanvasObjectCallback) {
                    this.pasteCanvasObjectCallback();
                }
            }

            // Alt+A - Enter Align mode (PowerPoint-style)
            if (e.altKey && e.key.toLowerCase() === 'a' && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                this.modeHandlers.enterAlignMode();
                return;
            }

            // Alt+F - Bring to Front (direct)
            if (e.altKey && e.key.toLowerCase() === 'f' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                if (this.arrangeCallback) {
                    this.arrangeCallback('front');
                    this.updateStatusBar('Brought to front');
                }
                return;
            }

            // Alt+B - Send to Back (direct)
            if (e.altKey && e.key.toLowerCase() === 'b' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                if (this.arrangeCallback) {
                    this.arrangeCallback('back');
                    this.updateStatusBar('Sent to back');
                }
                return;
            }

            // Alt+Z - Enter Size mode (Alt+S is reserved for global navigation to Scholar)
            if (e.altKey && e.key.toLowerCase() === 'z' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                this.modeHandlers.enterSizeMode();
                return;
            }

            // Alt+T - Toggle theme (area-responsive: canvas-only in canvas pane, global elsewhere)
            if (e.altKey && e.key.toLowerCase() === 't' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                this.modeHandlers.handleAreaResponsiveThemeToggle();
                return;
            }

            // Ctrl+G - Group
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'g' && !e.shiftKey) {
                e.preventDefault();
                if (this.groupCallback) {
                    this.groupCallback();
                }
                return;
            }

            // Ctrl+Shift+G - Ungroup
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'g') {
                e.preventDefault();
                if (this.ungroupCallback) {
                    this.ungroupCallback();
                }
                return;
            }

            // Handle mode shortcuts (align, arrange, size, alignByAxis)
            if (this.modeHandlers.isAnyModeActive()) {
                e.preventDefault();
                this.modeHandlers.handleModeKey(e.key);
                return;
            }

            // Arrow keys - Move (normal) or Resize (with Shift)
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                e.preventDefault();
                const direction = e.key.replace('Arrow', '').toLowerCase() as 'up' | 'down' | 'left' | 'right';
                if (this.nudgeCallback) {
                    this.nudgeCallback(direction, e.shiftKey);
                }
                return;
            }

            // Delete key - Delete selected object from canvas
            if (e.key === 'Delete' || e.key === 'Backspace') {
                e.preventDefault();
                if (this.deleteSelectedCallback) {
                    this.deleteSelectedCallback();
                }
            }

            // Escape key - Exit modes (element selection, etc.)
            if (e.key === 'Escape') {
                e.preventDefault();
                this.modeHandlers.clearModes();
                if (this.escapeCallback) {
                    this.escapeCallback();
                }
                return;
            }

            // Ctrl+D - Duplicate selected object
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
                e.preventDefault();
                if (this.duplicateSelectedCallback) {
                    this.duplicateSelectedCallback();
                }
            }

            // + key - Zoom in (view) or canvas size increase (with Ctrl, only when canvas focused)
            if (e.key === '+' || e.key === '=') {
                if ((e.ctrlKey || e.metaKey) && this.isCanvasFocused()) {
                    // Ctrl + = Canvas size increase (only when canvas has focus)
                    // Already handled by capture listener, skip here
                    return;
                } else if (!(e.ctrlKey || e.metaKey)) {
                    // Plain + = Zoom in view
                    e.preventDefault();
                    if (this.zoomInCallback) {
                        this.zoomInCallback();
                    }
                }
                // If Ctrl++ but canvas not focused, let browser handle zoom
            }

            // - key - Zoom out (view) or canvas size decrease (with Ctrl, only when canvas focused)
            if (e.key === '-' || e.key === '_') {
                if ((e.ctrlKey || e.metaKey) && this.isCanvasFocused()) {
                    // Ctrl - = Canvas size decrease (only when canvas has focus)
                    // Already handled by capture listener, skip here
                    return;
                } else if (!(e.ctrlKey || e.metaKey)) {
                    // Plain - = Zoom out view
                    e.preventDefault();
                    if (this.zoomOutCallback) {
                        this.zoomOutCallback();
                    }
                }
                // If Ctrl+- but canvas not focused, let browser handle zoom
            }

            // 0 key - Fit to window (view) or reset canvas size (with Ctrl, only when canvas focused)
            if (e.key === '0') {
                if ((e.ctrlKey || e.metaKey) && this.isCanvasFocused()) {
                    // Ctrl 0 = Reset canvas size to default (only when canvas has focus)
                    // Already handled by capture listener, skip here
                    return;
                } else if (!(e.ctrlKey || e.metaKey)) {
                    // Plain 0 = Fit view to window
                    e.preventDefault();
                    if (this.zoomToFitCallback) {
                        this.zoomToFitCallback();
                    }
                }
                // If Ctrl+0 but canvas not focused, let browser handle reset
            }

            // G key or Space - Toggle grid
            if (e.key === 'g' || e.key === 'G' || e.key === ' ') {
                if (!e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    if (this.toggleGridCallback) {
                        this.toggleGridCallback();
                    }
                }
            }

            // Space - Enable pan mode cursor
            if (e.key === ' ') {
                e.preventDefault();
                const canvasContainer = document.getElementById('canvas-container');
                if (canvasContainer && !(canvasContainer as any).isPanning) {
                    canvasContainer.style.cursor = 'grab';
                }
            }
        });

        // Space key release - Disable pan mode cursor
        document.addEventListener('keyup', (e: KeyboardEvent) => {
            if (e.key === ' ') {
                const canvasContainer = document.getElementById('canvas-container');
                if (canvasContainer) {
                    canvasContainer.style.cursor = 'default';
                }
            }
        });

        console.log('[KeyboardShortcuts] Keyboard shortcuts initialized');
    }

}
