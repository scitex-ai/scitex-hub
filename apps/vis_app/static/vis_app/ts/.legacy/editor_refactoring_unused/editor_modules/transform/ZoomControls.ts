/**
 * Zoom Controls
 * Handles zoom and pan user interactions
 */

import { Point } from '../types';

export class ZoomControls {
    private canvas: any;
    private isPanning: boolean = false;
    private panStartPoint: Point | null = null;
    private wheelThrottleFrame: number | null = null;
    private pendingTransform: (() => void) | null = null;
    private onZoomChange: (zoom: number, offset: Point) => void;
    private onPanChange: (offset: Point) => void;

    constructor(
        canvas: any,
        callbacks: {
            onZoomChange: (zoom: number, offset: Point) => void;
            onPanChange: (offset: Point) => void;
        }
    ) {
        this.canvas = canvas;
        this.onZoomChange = callbacks.onZoomChange;
        this.onPanChange = callbacks.onPanChange;
    }

    /**
     * Setup wheel event handling for ruler areas and canvas wrapper
     */
    public setupWrapperWheelHandling(zoomLevel: number, panOffset: Point): void {
        const canvasWrapper = document.querySelector('.vis-canvas-wrapper') as HTMLElement;
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;

        if (!canvasWrapper || !rulersArea) return;

        // Add wheel event handler with throttling
        const handleWheel = (e: WheelEvent) => {
            // Only handle events on the wrapper or ruler elements, not the canvas itself
            const target = e.target as HTMLElement;
            const isCanvasElement = target.tagName === 'CANVAS' || target.closest('#vis-canvas');

            // Let the canvas handler deal with canvas events
            if (isCanvasElement) return;

            e.preventDefault();
            e.stopPropagation();

            if (e.ctrlKey || e.metaKey) {
                // Ctrl+Wheel = Zoom
                const delta = e.deltaY;
                const oldZoom = zoomLevel;
                let newZoom = oldZoom * (0.999 ** delta);

                // Limit zoom range
                if (newZoom > 5) newZoom = 5;  // Max 500%
                if (newZoom < 0.1) newZoom = 0.1;  // Min 10%

                // Center zoom on wrapper center when not on canvas
                const wrapperRect = canvasWrapper.getBoundingClientRect();
                const centerX = wrapperRect.width / 2;
                const centerY = wrapperRect.height / 2;
                const zoomRatio = newZoom / oldZoom;
                const newPanOffset = {
                    x: centerX - (centerX - panOffset.x) * zoomRatio,
                    y: centerY - (centerY - panOffset.y) * zoomRatio,
                };

                // Throttle updates using requestAnimationFrame
                this.pendingTransform = () => {
                    this.onZoomChange(newZoom, newPanOffset);
                };

                if (!this.wheelThrottleFrame) {
                    this.wheelThrottleFrame = requestAnimationFrame(() => {
                        if (this.pendingTransform) {
                            this.pendingTransform();
                            this.pendingTransform = null;
                        }
                        this.wheelThrottleFrame = null;
                    });
                }
            } else {
                // Regular wheel = Pan
                const newPanOffset = {
                    x: panOffset.x - e.deltaX,
                    y: panOffset.y - e.deltaY,
                };

                // Throttle pan updates
                this.pendingTransform = () => {
                    this.onPanChange(newPanOffset);
                };

                if (!this.wheelThrottleFrame) {
                    this.wheelThrottleFrame = requestAnimationFrame(() => {
                        if (this.pendingTransform) {
                            this.pendingTransform();
                            this.pendingTransform = null;
                        }
                        this.wheelThrottleFrame = null;
                    });
                }
            }
        };

        // Add wheel event listeners to wrapper and rulers area
        canvasWrapper.addEventListener('wheel', handleWheel, { passive: false });
        rulersArea.addEventListener('wheel', handleWheel, { passive: false });

        console.log('[ZoomControls] Wrapper wheel handling initialized with throttling');
    }

    /**
     * Setup ruler dragging for panning
     */
    public setupRulerDragging(panOffset: Point): void {
        const rulerHorizontal = document.getElementById('ruler-horizontal');
        const rulerVertical = document.getElementById('ruler-vertical');
        const rulerHorizontalBottom = document.getElementById('ruler-horizontal-bottom');
        const rulerVerticalRight = document.getElementById('ruler-vertical-right');
        const rulerCorners = document.querySelectorAll('.ruler-corner');

        const rulers = [
            rulerHorizontal,
            rulerVertical,
            rulerHorizontalBottom,
            rulerVerticalRight,
            ...Array.from(rulerCorners)
        ].filter(r => r) as HTMLElement[];

        rulers.forEach(ruler => {
            // Set cursor style
            ruler.style.cursor = 'grab';

            // Mouse down on ruler
            ruler.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this.isPanning = true;
                this.panStartPoint = { x: e.clientX, y: e.clientY };
                ruler.style.cursor = 'grabbing';
            });

            // Mouse enter/leave for cursor feedback
            ruler.addEventListener('mouseenter', () => {
                if (!this.isPanning) ruler.style.cursor = 'grab';
            });

            ruler.addEventListener('mouseleave', () => {
                if (!this.isPanning) ruler.style.cursor = 'default';
            });
        });

        // Global mouse move and up for ruler dragging
        document.addEventListener('mousemove', (e) => {
            if (this.isPanning && this.panStartPoint) {
                let deltaX = e.clientX - this.panStartPoint.x;
                let deltaY = e.clientY - this.panStartPoint.y;

                // Alt key = Fine-tuned panning (10% speed)
                if (e.altKey) {
                    deltaX *= 0.1;
                    deltaY *= 0.1;
                }

                const newPanOffset = {
                    x: panOffset.x + deltaX,
                    y: panOffset.y + deltaY,
                };
                this.onPanChange(newPanOffset);

                this.panStartPoint = { x: e.clientX, y: e.clientY };
            }
        });

        document.addEventListener('mouseup', () => {
            if (this.isPanning) {
                this.isPanning = false;
                this.panStartPoint = null;

                // Reset all ruler cursors
                rulers.forEach(ruler => {
                    ruler.style.cursor = 'grab';
                });
            }
        });
    }
}
