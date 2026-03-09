/**
 * Alignment Tools
 * PowerPoint-style object alignment and distribution tools
 */

export class AlignmentTools {
    private canvas: any;
    private historyManager: any;
    private updateStatus: (message: string) => void;

    constructor(
        canvas: any,
        options: {
            historyManager: any;
            updateStatus: (message: string) => void;
        }
    ) {
        this.canvas = canvas;
        this.historyManager = options.historyManager;
        this.updateStatus = options.updateStatus;
    }

    /**
     * Align selected objects to the left edge
     */
    public alignLeft(): void {
        const selected = this.getSelectedObjects();
        if (selected.length < 2) {
            this.updateStatus('Select at least 2 objects to align');
            return;
        }

        const minLeft = Math.min(...selected.map((obj: any) => obj.left));
        selected.forEach((obj: any) => {
            obj.set('left', minLeft);
            obj.setCoords();
        });

        this.canvas?.renderAll();
        this.historyManager?.saveToHistory();
        this.updateStatus(`${selected.length} objects aligned left`);
    }

    /**
     * Align selected objects to horizontal center
     */
    public alignCenter(): void {
        const selected = this.getSelectedObjects();
        if (selected.length < 2) {
            this.updateStatus('Select at least 2 objects to align');
            return;
        }

        const centers = selected.map((obj: any) => obj.left + (obj.getBoundingRect().width / 2));
        const avgCenter = centers.reduce((a, b) => a + b, 0) / centers.length;

        selected.forEach((obj: any) => {
            const newLeft = avgCenter - (obj.getBoundingRect().width / 2);
            obj.set('left', newLeft);
            obj.setCoords();
        });

        this.canvas?.renderAll();
        this.historyManager?.saveToHistory();
        this.updateStatus(`${selected.length} objects aligned center`);
    }

    /**
     * Align selected objects to the right edge
     */
    public alignRight(): void {
        const selected = this.getSelectedObjects();
        if (selected.length < 2) {
            this.updateStatus('Select at least 2 objects to align');
            return;
        }

        const maxRight = Math.max(...selected.map((obj: any) => obj.left + obj.getBoundingRect().width));
        selected.forEach((obj: any) => {
            obj.set('left', maxRight - obj.getBoundingRect().width);
            obj.setCoords();
        });

        this.canvas?.renderAll();
        this.historyManager?.saveToHistory();
        this.updateStatus(`${selected.length} objects aligned right`);
    }

    /**
     * Align selected objects to the top edge
     */
    public alignTop(): void {
        const selected = this.getSelectedObjects();
        if (selected.length < 2) {
            this.updateStatus('Select at least 2 objects to align');
            return;
        }

        const minTop = Math.min(...selected.map((obj: any) => obj.top));
        selected.forEach((obj: any) => {
            obj.set('top', minTop);
            obj.setCoords();
        });

        this.canvas?.renderAll();
        this.historyManager?.saveToHistory();
        this.updateStatus(`${selected.length} objects aligned top`);
    }

    /**
     * Align selected objects to vertical middle
     */
    public alignMiddle(): void {
        const selected = this.getSelectedObjects();
        if (selected.length < 2) {
            this.updateStatus('Select at least 2 objects to align');
            return;
        }

        const middles = selected.map((obj: any) => obj.top + (obj.getBoundingRect().height / 2));
        const avgMiddle = middles.reduce((a, b) => a + b, 0) / middles.length;

        selected.forEach((obj: any) => {
            const newTop = avgMiddle - (obj.getBoundingRect().height / 2);
            obj.set('top', newTop);
            obj.setCoords();
        });

        this.canvas?.renderAll();
        this.historyManager?.saveToHistory();
        this.updateStatus(`${selected.length} objects aligned middle`);
    }

    /**
     * Align selected objects to the bottom edge
     */
    public alignBottom(): void {
        const selected = this.getSelectedObjects();
        if (selected.length < 2) {
            this.updateStatus('Select at least 2 objects to align');
            return;
        }

        const maxBottom = Math.max(...selected.map((obj: any) => obj.top + obj.getBoundingRect().height));
        selected.forEach((obj: any) => {
            obj.set('top', maxBottom - obj.getBoundingRect().height);
            obj.setCoords();
        });

        this.canvas?.renderAll();
        this.historyManager?.saveToHistory();
        this.updateStatus(`${selected.length} objects aligned bottom`);
    }

    /**
     * Distribute selected objects horizontally with equal spacing
     */
    public distributeHorizontally(): void {
        const selected = this.getSelectedObjects();
        if (selected.length < 3) {
            this.updateStatus('Select at least 3 objects to distribute');
            return;
        }

        // Sort by left position
        const sorted = selected.sort((a: any, b: any) => a.left - b.left);
        const leftMost = sorted[0].left;
        const rightMost = sorted[sorted.length - 1].left + sorted[sorted.length - 1].getBoundingRect().width;
        const totalSpace = rightMost - leftMost;

        // Calculate total width of all objects
        const totalObjWidth = sorted.reduce((sum: number, obj: any) => sum + obj.getBoundingRect().width, 0);
        const gap = (totalSpace - totalObjWidth) / (sorted.length - 1);

        let currentLeft = leftMost;
        sorted.forEach((obj: any, index: number) => {
            if (index !== 0 && index !== sorted.length - 1) {
                obj.set('left', currentLeft);
                obj.setCoords();
            }
            currentLeft += obj.getBoundingRect().width + gap;
        });

        this.canvas?.renderAll();
        this.historyManager?.saveToHistory();
        this.updateStatus(`${selected.length} objects distributed horizontally`);
    }

    /**
     * Distribute selected objects vertically with equal spacing
     */
    public distributeVertically(): void {
        const selected = this.getSelectedObjects();
        if (selected.length < 3) {
            this.updateStatus('Select at least 3 objects to distribute');
            return;
        }

        // Sort by top position
        const sorted = selected.sort((a: any, b: any) => a.top - b.top);
        const topMost = sorted[0].top;
        const bottomMost = sorted[sorted.length - 1].top + sorted[sorted.length - 1].getBoundingRect().height;
        const totalSpace = bottomMost - topMost;

        // Calculate total height of all objects
        const totalObjHeight = sorted.reduce((sum: number, obj: any) => sum + obj.getBoundingRect().height, 0);
        const gap = (totalSpace - totalObjHeight) / (sorted.length - 1);

        let currentTop = topMost;
        sorted.forEach((obj: any, index: number) => {
            if (index !== 0 && index !== sorted.length - 1) {
                obj.set('top', currentTop);
                obj.setCoords();
            }
            currentTop += obj.getBoundingRect().height + gap;
        });

        this.canvas?.renderAll();
        this.historyManager?.saveToHistory();
        this.updateStatus(`${selected.length} objects distributed vertically`);
    }

    /**
     * Get selected objects from canvas
     */
    private getSelectedObjects(): any[] {
        if (!this.canvas) return [];

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject) return [];

        // If it's a selection group, get all objects
        if (activeObject.type === 'activeSelection') {
            return (activeObject as any).getObjects();
        }

        // Single object
        return [activeObject];
    }
}
