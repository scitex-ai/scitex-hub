/**
 * SelectionManager - Handles object selection and clipboard operations
 *
 * Responsibilities:
 * - Get active object(s)
 * - Select all objects
 * - Copy/paste objects
 * - Duplicate objects
 * - Clear selection
 *
 * Dependencies:
 * - Canvas instance (Fabric.js)
 * - Status callback (optional, for user feedback)
 */

export class SelectionManager {
    private clipboard: any = null;

    constructor(
        private canvas: any,
        private statusCallback?: (message: string) => void
    ) {
        console.log('[SelectionManager] Initialized');
    }

    /**
     * Get active object (selected object or group)
     */
    public getActiveObject(): any {
        return this.canvas?.getActiveObject() || null;
    }

    /**
     * Select all selectable objects on canvas
     */
    public selectAll(): void {
        if (!this.canvas) return;

        // Get all selectable objects (exclude grid, guidelines, etc.)
        const objects = this.canvas.getObjects().filter((obj: any) => {
            return obj.selectable !== false &&
                   obj.id !== 'grid-line' &&
                   obj.id !== 'column-guide' &&
                   !obj.isAlignmentLine;
        });

        if (objects.length === 0) {
            if (this.statusCallback) {
                this.statusCallback('No objects to select');
            }
            return;
        }

        // Deselect any current selection
        this.canvas.discardActiveObject();

        // Create new selection with all objects
        const selection = new (window as any).fabric.ActiveSelection(objects, {
            canvas: this.canvas
        });
        this.canvas.setActiveObject(selection);
        this.canvas.renderAll();

        if (this.statusCallback) {
            this.statusCallback(`Selected ${objects.length} objects`);
        }

        console.log(`[SelectionManager] Selected all ${objects.length} objects`);
    }

    /**
     * Copy active object to clipboard
     */
    public copyActiveObject(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusCallback) {
                this.statusCallback('No object selected to copy');
            }
            return;
        }

        active.clone((cloned: any) => {
            this.clipboard = cloned;
            if (this.statusCallback) {
                this.statusCallback('Object copied');
            }
            console.log('[SelectionManager] Object copied to clipboard');
        });
    }

    /**
     * Paste object from clipboard
     */
    public pasteObject(saveUndoCallback?: () => void, saveContentCallback?: () => void): void {
        if (!this.canvas || !this.clipboard) {
            if (this.statusCallback) {
                this.statusCallback('Nothing to paste');
            }
            return;
        }

        // Save undo state before pasting (if callback provided)
        if (saveUndoCallback) {
            saveUndoCallback();
        }

        this.clipboard.clone((cloned: any) => {
            cloned.set({
                left: (this.clipboard.left || 0) + 20,
                top: (this.clipboard.top || 0) + 20,
                evented: true,
            });

            this.canvas!.add(cloned);
            this.canvas!.setActiveObject(cloned);
            this.canvas!.renderAll();

            // Save canvas content (if callback provided)
            if (saveContentCallback) {
                saveContentCallback();
            }

            // Update clipboard position for cascading pastes
            this.clipboard.left = cloned.left;
            this.clipboard.top = cloned.top;

            if (this.statusCallback) {
                this.statusCallback('Object pasted');
            }
            console.log('[SelectionManager] Object pasted from clipboard');
        });
    }

    /**
     * Duplicate active object (copy + paste in one operation)
     */
    public duplicateActiveObject(saveUndoCallback?: () => void, saveContentCallback?: () => void): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusCallback) {
                this.statusCallback('No object selected to duplicate');
            }
            return;
        }

        // Save undo state before duplicating (if callback provided)
        if (saveUndoCallback) {
            saveUndoCallback();
        }

        active.clone((cloned: any) => {
            cloned.set({
                left: (active.left || 0) + 20,
                top: (active.top || 0) + 20,
            });
            this.canvas!.add(cloned);
            this.canvas!.setActiveObject(cloned);
            this.canvas!.renderAll();

            // Save canvas content (if callback provided)
            if (saveContentCallback) {
                saveContentCallback();
            }

            if (this.statusCallback) {
                this.statusCallback('Object duplicated');
            }
            console.log('[SelectionManager] Object duplicated');
        });
    }

    /**
     * Clear selection (deselect all objects)
     */
    public clearSelection(): void {
        if (!this.canvas) return;

        this.canvas.discardActiveObject();
        this.canvas.renderAll();

        console.log('[SelectionManager] Selection cleared');
    }

    /**
     * Get clipboard status (for UI feedback)
     */
    public hasClipboard(): boolean {
        return this.clipboard !== null;
    }

    /**
     * Clear clipboard
     */
    public clearClipboard(): void {
        this.clipboard = null;
        console.log('[SelectionManager] Clipboard cleared');
    }
}
