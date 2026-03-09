/**
 * Panel Manager
 * Handles multi-panel layouts for scientific figures
 */

import { PanelLayout, PanelMetadata, LabelStyle, JournalPreset, FONT_SIZES } from '../types';

export class PanelManager {
    private canvas: any;
    private currentLayout: string = '1x1';
    private panelBorders: any[] = [];
    private panelLabels: any[] = [];
    private panelMetadata: PanelMetadata[] = [];
    private labelStyle: LabelStyle = 'uppercase';
    private darkCanvasMode: boolean = false;
    private getCurrentPreset: () => JournalPreset | null;
    private updateStatus: (message: string) => void;

    constructor(
        canvas: any,
        options: {
            getCurrentPreset: () => JournalPreset | null;
            updateStatus: (message: string) => void;
            darkCanvasMode?: boolean;
            labelStyle?: LabelStyle;
        }
    ) {
        this.canvas = canvas;
        this.getCurrentPreset = options.getCurrentPreset;
        this.updateStatus = options.updateStatus;
        this.darkCanvasMode = options.darkCanvasMode || false;
        this.labelStyle = options.labelStyle || 'uppercase';
    }

    /**
     * Set panel layout
     */
    public setLayout(layout: string): void {
        this.currentLayout = layout;
        console.log(`[PanelManager] Layout set to: ${layout}`);

        // Highlight active button
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
     * Generate panel layout on canvas
     */
    public generatePanelLayout(layout: string): void {
        if (!this.canvas) return;

        // Clear existing panels
        this.clearPanelBorders();
        this.panelMetadata = [];

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

                // Create panel border
                const borderColor = this.darkCanvasMode ? '#666666' : '#999999';

                const border = new (window as any).fabric.Rect({
                    left: x,
                    top: y,
                    width: panelWidth - 4,
                    height: panelHeight - 4,
                    fill: 'transparent',
                    stroke: borderColor,
                    strokeWidth: 2,
                    strokeDashArray: [5, 5],
                    selectable: false,
                    evented: false,
                });

                border.set('id', `panel-border-${baseLabel}`);
                border.set('panelId', baseLabel);

                this.canvas.add(border);
                this.canvas.sendToBack(border);
                this.panelBorders.push(border);

                // Create panel label
                const preset = this.getCurrentPreset();
                const fontFamily = preset?.font_family || 'Arial';
                const labelColor = this.darkCanvasMode ? '#ffffff' : '#000000';

                const text = new (window as any).fabric.Text(displayLabel, {
                    left: x + 10,
                    top: y + 10,
                    fontSize: FONT_SIZES.panelLabel,
                    fontFamily: fontFamily,
                    fontWeight: 'bold',
                    fill: labelColor,
                    selectable: true,
                    hasControls: false,
                    lockScalingX: true,
                    lockScalingY: true,
                    lockRotation: true,
                    hoverCursor: 'move',
                });

                text.set('id', `panel-label-${baseLabel}`);
                text.set('panelId', baseLabel);

                this.canvas.add(text);
                this.canvas.bringToFront(text);
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
        console.log(`[PanelManager] Generated ${layoutConfig.panels.length} panels`);
    }

    /**
     * Format panel label based on style
     */
    private formatPanelLabel(baseLabel: string): string {
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
     * Update panel labels based on current style
     */
    public updatePanelLabels(): void {
        if (!this.canvas) return;

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
     * Get layout configuration
     */
    private getLayoutConfig(layout: string): PanelLayout | null {
        const configs: { [key: string]: PanelLayout } = {
            '1x1': { rows: 1, cols: 1, panels: ['A'] },
            '2x1': { rows: 1, cols: 2, panels: ['A', 'B'] },
            '1x2': { rows: 2, cols: 1, panels: ['A', 'B'] },
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
     * Clear panel borders and labels
     */
    public clearPanelBorders(): void {
        if (!this.canvas) return;

        const objects = this.canvas.getObjects();
        objects.forEach((obj: any) => {
            if (obj.id && (obj.id.startsWith('panel-border-') || obj.id.startsWith('panel-label-'))) {
                this.canvas.remove(obj);
            }
        });

        this.panelBorders = [];
        this.panelLabels = [];
        this.panelMetadata = [];

        this.canvas.renderAll();
    }

    /**
     * Get current layout
     */
    public getCurrentLayout(): string {
        return this.currentLayout;
    }

    /**
     * Get panel metadata
     */
    public getPanelMetadata(): PanelMetadata[] {
        return this.panelMetadata;
    }

    /**
     * Set label style
     */
    public setLabelStyle(style: LabelStyle): void {
        this.labelStyle = style;
        this.updatePanelLabels();
    }

    /**
     * Set dark mode
     */
    public setDarkMode(dark: boolean): void {
        this.darkCanvasMode = dark;
        // Regenerate current layout with new colors
        if (this.currentLayout) {
            this.generatePanelLayout(this.currentLayout);
        }
    }
}
