/**
 * Panel Layout Manager
 * Manages multi-panel figure layouts with draggable labels
 */

interface PanelLayout {
    rows: number;
    cols: number;
    panels: string[];
}

interface PanelMetadata {
    id: string;
    position: string;  // 'A', 'B', 'C', etc.
    order: number;     // 0, 1, 2, etc.
    x: number;
    y: number;
    width: number;
    height: number;
    borderObject?: any;
    labelObject?: any;
}

export class PanelLayoutManager {
    private canvas: any;
    private panelBorders: any[] = [];
    private panelLabels: any[] = [];
    private panelMetadata: PanelMetadata[] = [];
    private labelStyle: 'uppercase' | 'lowercase' | 'numbers' = 'uppercase';
    private darkCanvasMode: boolean;
    private currentPreset: any;
    private fontSizes: any;
    private updateStatus: (message: string) => void;

    constructor(
        canvas: any,
        options: {
            darkCanvasMode: boolean;
            currentPreset: any;
            fontSizes: any;
            updateStatus: (message: string) => void;
        }
    ) {
        this.canvas = canvas;
        this.darkCanvasMode = options.darkCanvasMode;
        this.currentPreset = options.currentPreset;
        this.fontSizes = options.fontSizes;
        this.updateStatus = options.updateStatus;
    }

    /**
     * Set current layout and generate panel borders
     */
    public setLayout(layout: string): void {
        console.log(`[PanelLayoutManager] Layout set to: ${layout}`);

        // Highlight active icon button
        document.querySelectorAll('[data-layout]').forEach(btn => {
            btn.classList.remove('active');
        });
        const activeBtn = document.querySelector(`[data-layout="${layout}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }

        // Generate panel layout
        this.generatePanelLayout(layout);

        this.updateStatus(`Layout changed to ${layout}`);
    }

    /**
     * Generate panel borders and labels based on layout configuration
     */
    public generatePanelLayout(layout: string): void {
        if (!this.canvas) return;

        // Clear existing panel borders and labels
        this.clearPanelBorders();
        this.panelMetadata = [];  // Reset metadata

        const layoutConfig = this.getLayoutConfig(layout);
        if (!layoutConfig) return;

        const canvasWidth = this.canvas.getWidth();
        const canvasHeight = this.canvas.getHeight();

        const panelWidth = canvasWidth / layoutConfig.cols;
        const panelHeight = canvasHeight / layoutConfig.rows;

        let panelIndex = 0;

        for (let row = 0; row < layoutConfig.rows; row++) {
            for (let col = 0; col < layoutConfig.cols; col++) {
                if (panelIndex >= layoutConfig.panels.length) break;

                const x = col * panelWidth;
                const y = row * panelHeight;
                const baseLabel = layoutConfig.panels[panelIndex];
                const displayLabel = this.formatPanelLabel(baseLabel);

                // Create panel border (theme-aware colors)
                const borderColor = this.darkCanvasMode ? '#666666' : '#999999';

                const border = new (window as any).fabric.Rect({
                    left: 0,
                    top: 0,
                    width: panelWidth - 4,  // Slight padding
                    height: panelHeight - 4,
                    fill: 'transparent',
                    stroke: borderColor,
                    strokeWidth: 2,
                    strokeDashArray: [5, 5],
                } as any);

                // Create panel border group (without label for flexibility)
                border.set('id', `panel-border-${baseLabel}`);
                border.set('panelId', baseLabel);
                border.set('selectable', false);  // Border not selectable
                border.set('evented', false);
                border.set('left', x);
                border.set('top', y);

                this.canvas.add(border);
                this.canvas.sendToBack(border);
                this.panelBorders.push(border);

                // Create panel label as separate, independently movable object
                const fontFamily = this.currentPreset?.font_family || 'Arial';
                const labelColor = this.darkCanvasMode ? '#ffffff' : '#000000';

                const text = new (window as any).fabric.Text(displayLabel, {
                    left: x + 10,  // Position relative to panel
                    top: y + 10,
                    fontSize: this.fontSizes.panelLabel,  // 10pt for panel labels
                    fontFamily: fontFamily,
                    fontWeight: 'bold',
                    fill: labelColor,
                    selectable: true,
                    hasControls: false,  // No resize handles
                    lockScalingX: true,
                    lockScalingY: true,
                    lockRotation: true,
                    hoverCursor: 'move',
                } as any);
                text.set('id', `panel-label-${baseLabel}`);
                text.set('panelId', baseLabel);

                this.canvas.add(text);
                this.panelLabels.push(text);

                // Store metadata
                this.panelMetadata.push({
                    id: `panel-${baseLabel}`,
                    position: baseLabel,
                    order: panelIndex,
                    x: x,
                    y: y,
                    width: panelWidth,
                    height: panelHeight,
                    borderObject: border,
                    labelObject: text,
                });

                panelIndex++;
            }
        }

        this.canvas.renderAll();
        console.log(`[PanelLayoutManager] Generated ${layoutConfig.panels.length} draggable panels`);
    }

    /**
     * Format panel label based on current style
     */
    public formatPanelLabel(baseLabel: string): string {
        switch (this.labelStyle) {
            case 'uppercase':
                return baseLabel.toUpperCase();
            case 'lowercase':
                return baseLabel.toLowerCase();
            case 'numbers':
                // Convert A→1, B→2, etc.
                return (baseLabel.charCodeAt(0) - 64).toString();
            default:
                return baseLabel;
        }
    }

    /**
     * Update all panel labels based on current style
     */
    public updatePanelLabels(): void {
        if (!this.canvas) return;

        // Update all panel label text based on current style
        this.canvas.getObjects().forEach((obj: any) => {
            if (obj.id && obj.id.startsWith('panel-label-')) {
                const panelId = obj.panelId;
                if (panelId) {
                    const newLabel = this.formatPanelLabel(panelId);
                    obj.set('text', newLabel);
                }
            }
        });

        this.canvas.renderAll();
        this.updateStatus(`Labels updated to ${this.labelStyle}`);
    }

    /**
     * Clear all panel borders and labels
     */
    public clearPanelBorders(): void {
        if (!this.canvas) return;

        // Remove existing panel borders and labels
        const objects = this.canvas.getObjects();
        objects.forEach((obj: any) => {
            if (obj.id && (obj.id.startsWith('panel-border-') || obj.id.startsWith('panel-label-'))) {
                this.canvas!.remove(obj);
            }
        });

        this.panelBorders = [];
        this.panelLabels = [];
        this.panelMetadata = [];

        this.canvas.renderAll();
    }

    /**
     * Get layout configuration for a given layout string
     */
    private getLayoutConfig(layout: string): PanelLayout | null {
        const configs: { [key: string]: PanelLayout } = {
            '1x1': { rows: 1, cols: 1, panels: ['A'] },
            '1x2': { rows: 1, cols: 2, panels: ['A', 'B'] },
            '2x1': { rows: 2, cols: 1, panels: ['A', 'B'] },
            '2x2': { rows: 2, cols: 2, panels: ['A', 'B', 'C', 'D'] },
            '1x3': { rows: 1, cols: 3, panels: ['A', 'B', 'C'] },
            '3x1': { rows: 3, cols: 1, panels: ['A', 'B', 'C'] },
            '2x3': { rows: 2, cols: 3, panels: ['A', 'B', 'C', 'D', 'E', 'F'] },
            '3x2': { rows: 3, cols: 2, panels: ['A', 'B', 'C', 'D', 'E', 'F'] },
            '3x3': { rows: 3, cols: 3, panels: ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I'] },
        };

        return configs[layout] || null;
    }

    /**
     * Set label style
     */
    public setLabelStyle(style: 'uppercase' | 'lowercase' | 'numbers'): void {
        this.labelStyle = style;
        this.updatePanelLabels();
    }

    /**
     * Update dark mode state
     */
    public setDarkMode(darkMode: boolean): void {
        this.darkCanvasMode = darkMode;
    }

    /**
     * Update current preset
     */
    public setCurrentPreset(preset: any): void {
        this.currentPreset = preset;
    }

    /**
     * Get panel metadata
     */
    public getPanelMetadata(): PanelMetadata[] {
        return this.panelMetadata;
    }
}
