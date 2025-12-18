/**
 * NudgeManager - Handles arrow key object movement and resizing
 *
 * Responsibilities:
 * - Move objects with arrow keys (1px per press)
 * - Resize objects with Shift+arrow keys
 * - Debounced save after nudge operations
 */

export class NudgeManager {
    private nudgeSaveTimer: ReturnType<typeof setTimeout> | null = null;
    private saveCallback: () => void;

    constructor(
        private canvas: any,
        saveCallback: () => void,
        private statusCallback?: (message: string) => void
    ) {
        this.saveCallback = saveCallback;
        console.log('[NudgeManager] Initialized');
    }

    /**
     * Nudge selected objects (move or resize)
     * Arrow keys = move by 1px
     * Shift+Arrow = resize by 1px
     */
    public nudgeObjects(direction: 'up' | 'down' | 'left' | 'right', resize: boolean): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        const step = 1; // 1px per arrow press

        // Get objects to modify
        const objects = active.type === 'activeSelection'
            ? (active as any).getObjects()
            : [active];

        if (resize) {
            // Shift+Arrow = Resize
            objects.forEach((obj: any) => {
                const currentScaleX = obj.scaleX || 1;
                const currentScaleY = obj.scaleY || 1;
                const width = obj.width * currentScaleX;
                const height = obj.height * currentScaleY;

                switch (direction) {
                    case 'up': // Decrease height
                        obj.scaleY = Math.max(0.01, (height - step) / obj.height);
                        break;
                    case 'down': // Increase height
                        obj.scaleY = (height + step) / obj.height;
                        break;
                    case 'left': // Decrease width
                        obj.scaleX = Math.max(0.01, (width - step) / obj.width);
                        break;
                    case 'right': // Increase width
                        obj.scaleX = (width + step) / obj.width;
                        break;
                }
                obj.setCoords();
            });
        } else {
            // Arrow = Move
            objects.forEach((obj: any) => {
                switch (direction) {
                    case 'up':
                        obj.top = (obj.top || 0) - step;
                        break;
                    case 'down':
                        obj.top = (obj.top || 0) + step;
                        break;
                    case 'left':
                        obj.left = (obj.left || 0) - step;
                        break;
                    case 'right':
                        obj.left = (obj.left || 0) + step;
                        break;
                }
                obj.setCoords();
            });
        }

        this.canvas.renderAll();

        // Debounced save to avoid saving on every keypress
        this.debouncedSave();
    }

    /**
     * Debounced save after nudge
     */
    private debouncedSave(): void {
        if (this.nudgeSaveTimer) {
            clearTimeout(this.nudgeSaveTimer);
        }
        this.nudgeSaveTimer = setTimeout(() => {
            this.saveCallback();
            this.nudgeSaveTimer = null;
        }, 500);
    }

    /**
     * Cleanup
     */
    public destroy(): void {
        if (this.nudgeSaveTimer) {
            clearTimeout(this.nudgeSaveTimer);
            this.nudgeSaveTimer = null;
        }
    }
}
