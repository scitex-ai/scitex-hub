/**
 * Properties Panel
 * Displays and manages object properties panel
 */

export class PropertiesPanel {
    private canvas: any;
    private updateStatus: (message: string) => void;
    private duplicateObject: () => void;
    private bringToFront: () => void;
    private bringForward: () => void;
    private sendBackward: () => void;
    private sendToBack: () => void;

    constructor(
        canvas: any,
        options: {
            updateStatus: (message: string) => void;
            duplicateObject: () => void;
            bringToFront: () => void;
            bringForward: () => void;
            sendBackward: () => void;
            sendToBack: () => void;
        }
    ) {
        this.canvas = canvas;
        this.updateStatus = options.updateStatus;
        this.duplicateObject = options.duplicateObject;
        this.bringToFront = options.bringToFront;
        this.bringForward = options.bringForward;
        this.sendBackward = options.sendBackward;
        this.sendToBack = options.sendToBack;
    }

    /**
     * Update properties panel with active object information
     */
    public updatePropertiesPanel(): void {
        const activeObject = this.canvas?.getActiveObject();
        if (!activeObject) return;

        const propertiesContent = document.getElementById('properties-content');
        if (!propertiesContent) return;

        const type = activeObject.type || 'object';
        const left = Math.round(activeObject.left || 0);
        const top = Math.round(activeObject.top || 0);
        const width = Math.round((activeObject.width || 0) * (activeObject.scaleX || 1));
        const height = Math.round((activeObject.height || 0) * (activeObject.scaleY || 1));

        propertiesContent.innerHTML = `
            <div class="property-group">
                <label class="property-label">Type</label>
                <div class="property-value">${type}</div>
            </div>
            <div class="property-group">
                <label class="property-label">Position</label>
                <div class="property-value">X: ${left}px</div>
                <div class="property-value">Y: ${top}px</div>
            </div>
            <div class="property-group">
                <label class="property-label">Size</label>
                <div class="property-value">W: ${width}px</div>
                <div class="property-value">H: ${height}px</div>
            </div>
            <div class="property-group">
                <label class="property-label">Layer Order</label>
                <div style="display: flex; gap: 4px; margin-top: 6px;">
                    <button class="btn btn-sm" id="bring-to-front-btn" title="Bring to Front (Ctrl+Shift+])">
                        <i class="fas fa-angle-double-up"></i>
                    </button>
                    <button class="btn btn-sm" id="bring-forward-btn" title="Bring Forward (Ctrl+])">
                        <i class="fas fa-angle-up"></i>
                    </button>
                    <button class="btn btn-sm" id="send-backward-btn" title="Send Backward (Ctrl+[)">
                        <i class="fas fa-angle-down"></i>
                    </button>
                    <button class="btn btn-sm" id="send-to-back-btn" title="Send to Back (Ctrl+Shift+[)">
                        <i class="fas fa-angle-double-down"></i>
                    </button>
                </div>
            </div>
            <div class="property-group">
                <label class="property-label">Actions</label>
                <div style="display: flex; gap: 8px; margin-top: 6px;">
                    <button class="btn btn-sm btn-secondary" id="duplicate-object-btn" title="Duplicate (Ctrl+D)">
                        <i class="fas fa-copy"></i> Duplicate
                    </button>
                    <button class="btn btn-sm btn-danger" id="delete-object-btn" title="Delete (Del)">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `;

        // Add button handlers
        this.attachButtonHandlers();
    }

    /**
     * Attach event handlers to properties panel buttons
     */
    private attachButtonHandlers(): void {
        const deleteBtn = document.getElementById('delete-object-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                const active = this.canvas?.getActiveObject();
                if (active) {
                    this.canvas?.remove(active);
                    this.canvas?.renderAll();
                    this.clearPropertiesPanel();
                    this.updateStatus('Object deleted');
                }
            });
        }

        const duplicateBtn = document.getElementById('duplicate-object-btn');
        if (duplicateBtn) {
            duplicateBtn.addEventListener('click', () => this.duplicateObject());
        }

        const bringToFrontBtn = document.getElementById('bring-to-front-btn');
        if (bringToFrontBtn) {
            bringToFrontBtn.addEventListener('click', () => this.bringToFront());
        }

        const bringForwardBtn = document.getElementById('bring-forward-btn');
        if (bringForwardBtn) {
            bringForwardBtn.addEventListener('click', () => this.bringForward());
        }

        const sendBackwardBtn = document.getElementById('send-backward-btn');
        if (sendBackwardBtn) {
            sendBackwardBtn.addEventListener('click', () => this.sendBackward());
        }

        const sendToBackBtn = document.getElementById('send-to-back-btn');
        if (sendToBackBtn) {
            sendToBackBtn.addEventListener('click', () => this.sendToBack());
        }
    }

    /**
     * Clear properties panel content
     */
    public clearPropertiesPanel(): void {
        const propertiesContent = document.getElementById('properties-content');
        if (propertiesContent) {
            propertiesContent.innerHTML = '<p class="properties-empty">Select an object to edit properties</p>';
        }
    }
}
