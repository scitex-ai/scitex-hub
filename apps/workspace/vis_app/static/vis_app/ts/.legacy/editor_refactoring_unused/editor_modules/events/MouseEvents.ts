/**
 * MouseEvents - Manages mouse-related interactions
 *
 * Responsibilities:
 * - Setup mouse coordinate tracking
 * - Handle canvas selection events
 * - Coordinate with other managers for mouse interactions
 */

export class MouseEvents {
    constructor(
        private canvas: any,
        private onSelectionChange?: () => void
    ) {}

    /**
     * Setup mouse event listeners
     */
    public setupMouseEvents(): void {
        this.setupCoordinateTracking();
        this.setupSelectionHandlers();
        console.log('[MouseEvents] Mouse events initialized');
    }

    /**
     * Update canvas reference
     */
    public setCanvas(canvas: any): void {
        this.canvas = canvas;
    }

    /**
     * Setup mouse coordinate tracking display
     */
    private setupCoordinateTracking(): void {
        const canvasWrapper = document.querySelector('.vis-canvas-wrapper') as HTMLElement;
        if (!canvasWrapper) return;

        const handleMouseMove = (e: MouseEvent) => {
            const rect = canvasWrapper.getBoundingClientRect();
            const x = Math.round(e.clientX - rect.left);
            const y = Math.round(e.clientY - rect.top);

            const coordDisplay = document.getElementById('mouse-coordinates');
            if (coordDisplay) {
                coordDisplay.textContent = `X: ${x}px, Y: ${y}px`;
            }
        };

        const handleMouseLeave = () => {
            const coordDisplay = document.getElementById('mouse-coordinates');
            if (coordDisplay) {
                coordDisplay.textContent = 'X: -, Y: -';
            }
        };

        canvasWrapper.addEventListener('mousemove', handleMouseMove);
        canvasWrapper.addEventListener('mouseleave', handleMouseLeave);
    }

    /**
     * Setup canvas selection event handlers
     */
    private setupSelectionHandlers(): void {
        if (!this.canvas) return;

        // Selection created/updated
        this.canvas.on('selection:created', () => {
            if (this.onSelectionChange) {
                this.onSelectionChange();
            }
        });

        this.canvas.on('selection:updated', () => {
            if (this.onSelectionChange) {
                this.onSelectionChange();
            }
        });

        // Selection cleared
        this.canvas.on('selection:cleared', () => {
            if (this.onSelectionChange) {
                this.onSelectionChange();
            }
        });
    }
}
