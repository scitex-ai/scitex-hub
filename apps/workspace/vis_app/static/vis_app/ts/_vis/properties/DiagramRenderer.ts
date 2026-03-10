/**
 * DiagramRenderer - Handles blueprint diagram rendering
 *
 * Responsibilities:
 * - Update SVG diagram elements based on defaults
 * - Initialize diagram click handlers for editable fields
 * - Sync diagram text boxes with current defaults
 */

export interface DiagramRendererCallbacks {
    getCurrentDefaults: () => any;
    setCurrentDefault: (key: string, value: any) => void;
    updateYAMLTextarea: () => void;
    updatePreviewDebounced: () => void;
    getCurrentUnit: () => 'mm' | 'inch';
    mmToInch: (mm: number) => number;
}

export class DiagramRenderer {
    private callbacks: DiagramRendererCallbacks | null = null;

    public setCallbacks(callbacks: DiagramRendererCallbacks): void {
        this.callbacks = callbacks;
    }

    /**
     * Initialize click handlers for diagram text boxes
     */
    public initDiagramClickHandlers(): void {
        const diagramInputs = document.querySelectorAll('#preset-diagram input[data-field]');

        diagramInputs.forEach((input) => {
            const inputEl = input as HTMLInputElement;
            const fieldKey = inputEl.getAttribute('data-field');
            if (!fieldKey) return;

            inputEl.addEventListener('input', () => {
                if (this.callbacks) {
                    this.callbacks.setCurrentDefault(fieldKey, inputEl.value);
                    this.callbacks.updateYAMLTextarea();
                    this.callbacks.updatePreviewDebounced();
                }
            });

            inputEl.addEventListener('focus', () => {
                inputEl.style.borderColor = '#2196f3';
                inputEl.style.boxShadow = '0 0 0 2px rgba(33, 150, 243, 0.2)';
            });

            inputEl.addEventListener('blur', () => {
                inputEl.style.borderColor = '#ccc';
                inputEl.style.boxShadow = 'none';
            });
        });
    }

    /**
     * Update diagram from current defaults
     */
    public updateDiagram(): void {
        if (!this.callbacks) return;

        const d = this.callbacks.getCurrentDefaults();
        const unit = this.callbacks.getCurrentUnit();

        const titleInput = document.getElementById('diagram-title-input') as HTMLInputElement;
        const xlabelInput = document.getElementById('diagram-xlabel-input') as HTMLInputElement;
        const ylabelInput = document.getElementById('diagram-ylabel-input') as HTMLInputElement;
        const dpiEl = document.getElementById('diagram-dpi');
        const fontEl = document.getElementById('diagram-font');

        if (titleInput && titleInput.value !== (d.title || 'Title')) {
            titleInput.value = d.title || 'Title';
        }
        if (xlabelInput && xlabelInput.value !== (d.xlabel || 'X Label')) {
            xlabelInput.value = d.xlabel || 'X Label';
        }
        if (ylabelInput && ylabelInput.value !== (d.ylabel || 'Y Label')) {
            ylabelInput.value = d.ylabel || 'Y Label';
        }
        if (dpiEl) {
            dpiEl.textContent = `DPI: ${d.dpi || 300}`;
        }
        if (fontEl) {
            fontEl.textContent = `Font: ${d.font_family || 'Arial'}`;
        }

        const widthMm = d.axes_width_mm || 40;
        const heightMm = d.axes_height_mm || 28;
        const widthLabel = document.getElementById('diagram-width-label');
        const heightLabel = document.getElementById('diagram-height-label');

        if (widthLabel) {
            const displayWidth = unit === 'inch' ? this.callbacks.mmToInch(widthMm).toFixed(2) : widthMm;
            widthLabel.textContent = `${displayWidth}${unit}`;
        }
        if (heightLabel) {
            const displayHeight = unit === 'inch' ? this.callbacks.mmToInch(heightMm).toFixed(2) : heightMm;
            heightLabel.textContent = `${displayHeight}${unit}`;
        }

        const marginTop = d.margin_top_mm || 20;
        const marginLeft = d.margin_left_mm || 20;
        const marginTopLabel = document.getElementById('diagram-margin-top');
        const marginLeftLabel = document.getElementById('diagram-margin-left');

        if (marginTopLabel) {
            const displayMargin = unit === 'inch' ? this.callbacks.mmToInch(marginTop).toFixed(2) : marginTop;
            marginTopLabel.textContent = `${displayMargin}${unit}`;
        }
        if (marginLeftLabel) {
            const displayMargin = unit === 'inch' ? this.callbacks.mmToInch(marginLeft).toFixed(2) : marginLeft;
            marginLeftLabel.textContent = `${displayMargin}${unit}`;
        }

        const cropIndicator = document.getElementById('diagram-crop-indicator');
        if (cropIndicator) {
            cropIndicator.style.opacity = d.auto_crop ? '1' : '0';
        }

        this.updateDiagramGeometry(d);
    }

    /**
     * Update diagram geometry (axes and margins rectangles)
     */
    private updateDiagramGeometry(d: any): void {
        const axesRect = document.getElementById('diagram-axes');
        const marginsRect = document.getElementById('diagram-margins');

        const scale = 4;
        const widthMm = d.axes_width_mm || 40;
        const heightMm = d.axes_height_mm || 28;
        const marginMm = d.margin_left_mm || 20;

        const scaledWidth = widthMm * scale;
        const scaledHeight = heightMm * scale;
        const scaledMargin = marginMm * scale;

        if (axesRect) {
            const x = (340 - scaledWidth) / 2;
            const y = (200 - scaledHeight) / 2 + 30;

            axesRect.setAttribute('x', x.toString());
            axesRect.setAttribute('y', y.toString());
            axesRect.setAttribute('width', scaledWidth.toString());
            axesRect.setAttribute('height', scaledHeight.toString());
        }

        if (marginsRect) {
            const x = (340 - scaledWidth) / 2 - scaledMargin;
            const y = (200 - scaledHeight) / 2 + 30 - scaledMargin;
            const width = scaledWidth + scaledMargin * 2;
            const height = scaledHeight + scaledMargin * 2;

            marginsRect.setAttribute('x', x.toString());
            marginsRect.setAttribute('y', y.toString());
            marginsRect.setAttribute('width', width.toString());
            marginsRect.setAttribute('height', height.toString());
        }
    }

    /**
     * Update diagram text boxes from current defaults
     */
    public updateDiagramTextBoxes(): void {
        if (!this.callbacks) return;

        const d = this.callbacks.getCurrentDefaults();
        const titleInput = document.getElementById('diagram-title-input') as HTMLInputElement;
        const xlabelInput = document.getElementById('diagram-xlabel-input') as HTMLInputElement;
        const ylabelInput = document.getElementById('diagram-ylabel-input') as HTMLInputElement;

        if (titleInput) titleInput.value = d.title || 'Title';
        if (xlabelInput) xlabelInput.value = d.xlabel || 'X Label';
        if (ylabelInput) ylabelInput.value = d.ylabel || 'Y Label';
    }
}
