/**
 * KeyboardEvents - Manages all keyboard shortcuts and handlers
 *
 * Responsibilities:
 * - Setup keyboard event listeners
 * - Handle copy/paste/duplicate shortcuts
 * - Handle delete/backspace
 * - Handle zoom shortcuts (+, -, 0)
 * - Handle undo/redo (Ctrl+Z, Ctrl+Y)
 * - Handle layer ordering shortcuts
 * - Handle group/ungroup shortcuts
 * - Handle space key for pan mode cursor
 */

export interface KeyboardHandlers {
    onCopy?: () => void;
    onPaste?: () => void;
    onDuplicate?: () => void;
    onSave?: () => void;
    onDelete?: () => void;
    onBringToFront?: () => void;
    onSendToBack?: () => void;
    onBringForward?: () => void;
    onSendBackward?: () => void;
    onZoomIn?: () => void;
    onZoomOut?: () => void;
    onZoomToFit?: () => void;
    onUndo?: () => void;
    onRedo?: () => void;
    onGroup?: () => void;
    onUngroup?: () => void;
    onEnterGroup?: () => void;
}

export class KeyboardEvents {
    private isPanning: boolean = false;

    constructor(
        private canvas: any,
        private handlers: KeyboardHandlers = {}
    ) {}

    /**
     * Setup all keyboard event listeners
     */
    public setupKeyboardEvents(): void {
        this.setupKeydownHandler();
        this.setupKeyupHandler();
        console.log('[KeyboardEvents] Keyboard shortcuts initialized');
    }

    /**
     * Update canvas reference (when canvas changes)
     */
    public setCanvas(canvas: any): void {
        this.canvas = canvas;
    }

    /**
     * Update panning state (for space key cursor feedback)
     */
    public setIsPanning(isPanning: boolean): void {
        this.isPanning = isPanning;
    }

    /**
     * Setup keydown event handler
     */
    private setupKeydownHandler(): void {
        document.addEventListener('keydown', (e) => {
            const isInputFocused = document.activeElement?.tagName === 'INPUT' ||
                                   document.activeElement?.tagName === 'TEXTAREA';

            // Ctrl+C - Copy
            if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
                const activeObject = this.canvas?.getActiveObject();
                if (activeObject && !isInputFocused) {
                    e.preventDefault();
                    this.handlers.onCopy?.();
                }
            }

            // Ctrl+V - Paste
            if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
                if (!isInputFocused) {
                    e.preventDefault();
                    this.handlers.onPaste?.();
                }
            }

            // Ctrl+D or Cmd+D - Duplicate
            if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
                e.preventDefault();
                this.handlers.onDuplicate?.();
            }

            // Ctrl+S or Cmd+S - Save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.handlers.onSave?.();
            }

            // Delete or Backspace - Delete selected
            if (e.key === 'Delete' || e.key === 'Backspace') {
                const activeObject = this.canvas?.getActiveObject();
                if (activeObject && !isInputFocused) {
                    e.preventDefault();
                    this.handlers.onDelete?.();
                }
            }

            // Ctrl+Shift+] - Bring to front
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === '}') {
                e.preventDefault();
                this.handlers.onBringToFront?.();
            }

            // Ctrl+Shift+[ - Send to back
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === '{') {
                e.preventDefault();
                this.handlers.onSendToBack?.();
            }

            // Ctrl+] - Bring forward
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === ']') {
                e.preventDefault();
                this.handlers.onBringForward?.();
            }

            // Ctrl+[ - Send backward
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === '[') {
                e.preventDefault();
                this.handlers.onSendBackward?.();
            }

            // + key - Zoom in
            if ((e.key === '+' || e.key === '=') && !isInputFocused) {
                if (!e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    this.handlers.onZoomIn?.();
                }
            }

            // - key - Zoom out
            if ((e.key === '-' || e.key === '_') && !isInputFocused) {
                if (!e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    this.handlers.onZoomOut?.();
                }
            }

            // 0 key - Fit to window
            if (e.key === '0' && !isInputFocused) {
                if (!e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    this.handlers.onZoomToFit?.();
                }
            }

            // Ctrl+Z - Undo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                this.handlers.onUndo?.();
            }

            // Ctrl+Y or Ctrl+Shift+Z - Redo
            if (((e.ctrlKey || e.metaKey) && e.key === 'y') ||
                ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z')) {
                e.preventDefault();
                this.handlers.onRedo?.();
            }

            // Ctrl+G - Group selected objects
            if ((e.ctrlKey || e.metaKey) && (e.key === 'g' || e.key === 'G') && !e.shiftKey) {
                e.preventDefault();
                this.handlers.onGroup?.();
            }

            // Ctrl+Shift+G - Ungroup selected group
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'g' || e.key === 'G')) {
                e.preventDefault();
                this.handlers.onUngroup?.();
            }

            // Enter - Enter group to edit contents
            if (e.key === 'Enter' && !e.ctrlKey && !e.metaKey && !isInputFocused) {
                e.preventDefault();
                this.handlers.onEnterGroup?.();
            }

            // Space - Enable pan mode (visual feedback)
            if (e.key === ' ' && !e.ctrlKey && !e.metaKey && !isInputFocused) {
                e.preventDefault();
                const canvasEl = document.getElementById('vis-canvas');
                if (canvasEl && !this.isPanning) {
                    canvasEl.style.cursor = 'grab';
                }
            }
        });
    }

    /**
     * Setup keyup event handler
     */
    private setupKeyupHandler(): void {
        document.addEventListener('keyup', (e) => {
            // Space key release - Disable pan mode cursor
            if (e.key === ' ') {
                const canvasEl = document.getElementById('vis-canvas');
                if (canvasEl) {
                    canvasEl.style.cursor = 'default';
                }
            }
        });
    }
}
