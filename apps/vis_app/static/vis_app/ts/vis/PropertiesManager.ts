/**
 * PropertiesManager - Handles properties panel operations
 *
 * Responsibilities:
 * - Initialize properties panel tabs
 * - Switch between different property views (plot, format, layout, etc.)
 * - Update column dropdowns for plot configuration
 * - Manage properties panel state
 */

import { Dataset } from './types.ts';

export class PropertiesManager {
    private currentPropertiesTab: string = 'plot';

    // Plot property state
    private plotProperties = {
        lineWidth: 2,
        markerSize: 8,
    };

    // Reference to dynamic properties container
    private dynamicPropertiesEl: HTMLElement | null = null;
    private selectedItemInfoEl: HTMLElement | null = null;

    constructor(
        private getCurrentDataCallback?: () => Dataset | null
    ) {
        this.dynamicPropertiesEl = document.getElementById('dynamic-properties');
        this.selectedItemInfoEl = document.querySelector('.selected-item-info') as HTMLElement;
    }

    /**
     * Get current properties tab
     */
    public getCurrentPropertiesTab(): string {
        return this.currentPropertiesTab;
    }

    /**
     * Initialize properties tabs switching (legacy method - tabs removed in favor of dynamic properties)
     */
    public initPropertiesTabs(): void {
        const tabs = document.querySelectorAll('.properties-tab');

        // If tabs exist (old UI), initialize them
        if (tabs.length > 0) {
            const panels = document.querySelectorAll('.properties-panel');

            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const tabName = tab.getAttribute('data-props-tab');
                    if (!tabName) return;

                    // Update active tab
                    tabs.forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');

                    // Show corresponding panel
                    panels.forEach(p => p.classList.remove('active'));
                    const targetPanel = document.querySelector(`.properties-panel[data-props-panel="${tabName}"]`);
                    if (targetPanel) {
                        targetPanel.classList.add('active');
                    }

                    this.currentPropertiesTab = tabName;
                    console.log(`[PropertiesManager] Switched to properties tab: ${tabName}`);
                });
            });

            console.log('[PropertiesManager] Properties tabs initialized (legacy)');
        } else {
            // New dynamic properties UI
            console.log('[PropertiesManager] Dynamic properties initialized');
        }
    }

    /**
     * Setup property range sliders with value display
     */
    public setupPropertySliders(): void {
        // Find all range sliders in the properties panel
        const sliders = document.querySelectorAll('.property-range') as NodeListOf<HTMLInputElement>;

        sliders.forEach(slider => {
            // Get the adjacent value display span
            const valueSpan = slider.nextElementSibling as HTMLElement;

            if (valueSpan && valueSpan.classList.contains('property-value')) {
                // Set initial value
                valueSpan.textContent = slider.value;

                // Update value on input
                slider.addEventListener('input', () => {
                    const value = parseFloat(slider.value);
                    valueSpan.textContent = slider.value;

                    // Update internal state based on slider ID
                    if (slider.id === 'prop-line-width') {
                        this.plotProperties.lineWidth = value;
                        console.log(`[PropertiesManager] Line width: ${value}`);
                    } else if (slider.id === 'prop-marker-size') {
                        this.plotProperties.markerSize = value;
                        console.log(`[PropertiesManager] Marker size: ${value}`);
                    }
                });
            }
        });

        console.log(`[PropertiesManager] Property sliders initialized (${sliders.length} sliders)`);
    }

    /**
     * Get current plot properties
     */
    public getPlotProperties(): { lineWidth: number; markerSize: number } {
        return { ...this.plotProperties };
    }

    /**
     * Update column dropdowns in properties panel
     */
    public updateColumnDropdowns(): void {
        const currentData = this.getCurrentDataCallback?.();
        if (!currentData) return;

        const xColumnSelect = document.getElementById('prop-x-column') as HTMLSelectElement;
        const yColumnSelect = document.getElementById('prop-y-column') as HTMLSelectElement;

        if (xColumnSelect && yColumnSelect) {
            const options = currentData.columns.map(col =>
                `<option value="${col}">${col}</option>`
            ).join('');

            xColumnSelect.innerHTML = `<option value="">-- Select --</option>${options}`;
            yColumnSelect.innerHTML = `<option value="">-- Select --</option>${options}`;

            // Auto-select first two columns
            if (currentData.columns.length >= 2) {
                xColumnSelect.value = currentData.columns[0];
                yColumnSelect.value = currentData.columns[1];
            }

            console.log('[PropertiesManager] Column dropdowns updated');
        }
    }

    /**
     * Get selected columns from properties panel
     */
    public getSelectedColumns(): { xColumn: string, yColumn: string } {
        const xColSelect = document.getElementById('prop-x-column') as HTMLSelectElement;
        const yColSelect = document.getElementById('prop-y-column') as HTMLSelectElement;

        const currentData = this.getCurrentDataCallback?.();

        return {
            xColumn: xColSelect?.value || currentData?.columns[0] || '',
            yColumn: yColSelect?.value || currentData?.columns[1] || currentData?.columns[0] || ''
        };
    }

    /**
     * Set properties panel collapsed state
     */
    public setPropertiesCollapsed(collapsed: boolean): void {
        const propertiesPanel = document.querySelector('.vis-properties');
        if (propertiesPanel) {
            if (collapsed) {
                propertiesPanel.classList.add('collapsed');
            } else {
                propertiesPanel.classList.remove('collapsed');
            }
        }
    }

    /**
     * Toggle properties panel visibility
     */
    public togglePropertiesPanel(): void {
        const propertiesPanel = document.querySelector('.vis-properties');
        if (propertiesPanel) {
            const isCollapsed = propertiesPanel.classList.contains('collapsed');
            this.setPropertiesCollapsed(!isCollapsed);
            console.log(`[PropertiesManager] Properties panel ${isCollapsed ? 'expanded' : 'collapsed'}`);
        }
    }

    /**
     * Programmatically switch to a specific properties tab (legacy method, kept for compatibility)
     */
    public switchToTab(tabName: string): void {
        const tabs = document.querySelectorAll('.properties-tab');
        const panels = document.querySelectorAll('.properties-panel');

        // Find the target tab
        let targetTab: Element | null = null;
        tabs.forEach(tab => {
            if (tab.getAttribute('data-props-tab') === tabName) {
                targetTab = tab;
            }
        });

        if (!targetTab) {
            console.warn(`[PropertiesManager] Tab "${tabName}" not found`);
            return;
        }

        // Update active tab
        tabs.forEach(t => t.classList.remove('active'));
        targetTab.classList.add('active');

        // Show corresponding panel
        panels.forEach(p => p.classList.remove('active'));
        const targetPanel = document.querySelector(`.properties-panel[data-props-panel="${tabName}"]`);
        if (targetPanel) {
            targetPanel.classList.add('active');
        }

        this.currentPropertiesTab = tabName;
        console.log(`[PropertiesManager] Auto-switched to properties tab: ${tabName}`);
    }

    /**
     * Show properties for a specific element type
     */
    public showPropertiesFor(elementType: string, elementLabel: string, elementData?: any): void {
        if (!this.dynamicPropertiesEl || !this.selectedItemInfoEl) {
            console.warn('[PropertiesManager] Dynamic properties elements not found');
            return;
        }

        // Update selected item info header
        this.updateSelectedItemInfo(elementType, elementLabel);

        // Clear current properties
        this.dynamicPropertiesEl.innerHTML = '';

        // Load appropriate template based on element type
        let templateId = '';
        switch (elementType.toLowerCase()) {
            case 'figure':
                templateId = 'template-figure-props';
                break;
            case 'axis':
            case 'ax':
                templateId = 'template-axis-props';
                break;
            case 'labels':
                templateId = 'template-labels-props';
                break;
            case 'plot':
                templateId = 'template-plot-props';
                break;
            case 'guide':
            case 'legend':
            case 'colorbar':
                templateId = 'template-guide-props';
                break;
            case 'annotation':
                templateId = 'template-annotation-props';
                break;
            default:
                console.warn(`[PropertiesManager] Unknown element type: ${elementType}`);
                return;
        }

        // Clone and insert template
        const template = document.getElementById(templateId) as HTMLTemplateElement;
        if (template) {
            const content = template.content.cloneNode(true);
            this.dynamicPropertiesEl.appendChild(content);

            // Re-setup sliders after adding new content
            this.setupPropertySliders();

            // Populate with element data if provided
            if (elementData) {
                this.populateProperties(elementType, elementData);
            }

            console.log(`[PropertiesManager] Showing properties for ${elementType}: ${elementLabel}`);
        } else {
            console.warn(`[PropertiesManager] Template not found: ${templateId}`);
        }
    }

    /**
     * Update selected item info header
     */
    private updateSelectedItemInfo(elementType: string, elementLabel: string): void {
        if (!this.selectedItemInfoEl) return;

        const iconMap: { [key: string]: string } = {
            'figure': 'fa-chart-area',
            'axis': 'fa-crosshairs',
            'ax': 'fa-crosshairs',
            'labels': 'fa-tags',
            'plot': 'fa-chart-line',
            'guide': 'fa-compass',
            'legend': 'fa-square-check',
            'colorbar': 'fa-fill-drip',
            'annotation': 'fa-sticky-note',
            'element': 'fa-vector-square'
        };

        const icon = iconMap[elementType.toLowerCase()] || 'fa-info-circle';

        const headerEl = this.selectedItemInfoEl.querySelector('.selected-item-header');
        const labelEl = this.selectedItemInfoEl.querySelector('.selected-item-label');

        if (headerEl && labelEl) {
            headerEl.innerHTML = `
                <i class="fas ${icon} selected-item-icon"></i>
                <span class="selected-item-type">${this.capitalizeFirst(elementType)}</span>
            `;
            labelEl.textContent = elementLabel;
        }
    }

    /**
     * Populate properties with element data
     */
    private populateProperties(elementType: string, data: any): void {
        // TODO: Implement property population based on element type and data
        console.log('[PropertiesManager] Populating properties with data:', data);
    }

    /**
     * Capitalize first letter
     */
    private capitalizeFirst(str: string): string {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Show properties for a canvas object (fabric.js object)
     * Displays embedded metadata including axis_bbox_px for snap/align
     * Uses SciTeX Editor style with collapsible sections
     */
    public showCanvasObjectProperties(obj: any): void {
        if (!this.dynamicPropertiesEl || !this.selectedItemInfoEl) {
            console.warn('[PropertiesManager] Dynamic properties elements not found');
            return;
        }

        const name = obj.name || obj.type || 'Object';

        // Update header
        this.updateSelectedItemInfo('figure', name);

        // Build properties HTML with SciTeX-style collapsible sections
        let html = '';

        // BASIC PROPERTIES section
        html += `<div class="scitex-section">
            <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                <i class="fas fa-chevron-down"></i>
                <span>Basic Properties</span>
            </div>
            <div class="scitex-section-content">`;

        html += `<div class="property-group">
            <label class="property-label">Name</label>
            <input type="text" class="property-input" value="${name}" readonly>
        </div>`;

        html += `<div class="property-group">
            <label class="property-label">Type</label>
            <input type="text" class="property-input" value="${obj.type || 'unknown'}" readonly>
        </div>`;

        if (obj.width && obj.height) {
            const displayWidth = Math.round(obj.width * (obj.scaleX || 1));
            const displayHeight = Math.round(obj.height * (obj.scaleY || 1));
            html += `<div class="property-row">
                <div class="property-group half">
                    <label class="property-label">Width (px)</label>
                    <input type="text" class="property-input" value="${displayWidth}" readonly>
                </div>
                <div class="property-group half">
                    <label class="property-label">Height (px)</label>
                    <input type="text" class="property-input" value="${displayHeight}" readonly>
                </div>
            </div>`;
        }

        if (obj.left !== undefined && obj.top !== undefined) {
            html += `<div class="property-row">
                <div class="property-group half">
                    <label class="property-label">X Position</label>
                    <input type="text" class="property-input" value="${Math.round(obj.left)}" readonly>
                </div>
                <div class="property-group half">
                    <label class="property-label">Y Position</label>
                    <input type="text" class="property-input" value="${Math.round(obj.top)}" readonly>
                </div>
            </div>`;
        }

        html += `</div></div>`;

        // AXIS METADATA section (for SciTeX figures)
        html += `<div class="scitex-section">
            <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                <i class="fas fa-chevron-down"></i>
                <span>Axis Metadata</span>
            </div>
            <div class="scitex-section-content">`;

        if (obj.axisMetadata) {
            const meta = obj.axisMetadata;

            // Calculate current scale
            const scaleX = obj.scaleX || 1;
            const scaleY = obj.scaleY || 1;

            // axes_bbox_px - show scaled values
            if (meta.axes_bbox_px) {
                const bbox = meta.axes_bbox_px;
                // Apply scale to show actual current axis positions
                const scaledX0 = Math.round(bbox.x0 * scaleX);
                const scaledY0 = Math.round(bbox.y0 * scaleY);
                const scaledX1 = Math.round(bbox.x1 * scaleX);
                const scaledY1 = Math.round(bbox.y1 * scaleY);
                const scaledWidth = Math.round(bbox.width * scaleX);
                const scaledHeight = Math.round(bbox.height * scaleY);

                html += `<div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Y-Axis (x0)</label>
                        <input type="text" class="property-input" value="${scaledX0} px" readonly>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">X-Axis (y1)</label>
                        <input type="text" class="property-input" value="${scaledY1} px" readonly>
                    </div>
                </div>`;
                html += `<div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Right (x1)</label>
                        <input type="text" class="property-input" value="${scaledX1} px" readonly>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Top (y0)</label>
                        <input type="text" class="property-input" value="${scaledY0} px" readonly>
                    </div>
                </div>`;

                html += `<div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Plot Width</label>
                        <input type="text" class="property-input" value="${scaledWidth} px" readonly>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Plot Height</label>
                        <input type="text" class="property-input" value="${scaledHeight} px" readonly>
                    </div>
                </div>`;
            }

            // figure_size_px - show scaled values
            if (meta.figure_size_px) {
                const size = meta.figure_size_px;
                const scaledFigWidth = Math.round(size.width * scaleX);
                const scaledFigHeight = Math.round(size.height * scaleY);
                html += `<div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Fig Width</label>
                        <input type="text" class="property-input" value="${scaledFigWidth} px" readonly>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Fig Height</label>
                        <input type="text" class="property-input" value="${scaledFigHeight} px" readonly>
                    </div>
                </div>`;
            }

            html += `<div class="scitex-no-traces" style="color: var(--accent-primary); font-style: normal;">
                <i class="fas fa-check-circle"></i> Axis snap enabled
            </div>`;
        } else {
            html += `<div class="scitex-no-traces">
                No axis metadata (standard image)
            </div>`;
        }

        html += `</div></div>`;

        // RAW JSON section (for development)
        html += `<div class="scitex-section">
            <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                <i class="fas fa-chevron-down"></i>
                <span>Raw JSON</span>
            </div>
            <div class="scitex-section-content" style="display: none;">`;

        // Collect all metadata for JSON display
        const jsonData: any = {};

        if (obj.axisMetadata) {
            jsonData.axisMetadata = obj.axisMetadata;
        }

        if (obj.plotInfo) {
            jsonData.plotInfo = obj.plotInfo;
        }

        if (obj.csvData && obj.csvData.length > 0) {
            jsonData.csvDataInfo = {
                rows: obj.csvData.length,
                columns: obj.csvData[0]?.length || 0,
                headers: obj.csvData[0] || []
            };
        }

        // Add basic object info
        jsonData.fabricObject = {
            type: obj.type,
            name: obj.name,
            width: obj.width,
            height: obj.height,
            scaleX: obj.scaleX,
            scaleY: obj.scaleY,
            left: obj.left,
            top: obj.top,
            angle: obj.angle
        };

        if (Object.keys(jsonData).length > 0) {
            const jsonString = JSON.stringify(jsonData, null, 2);
            html += `<div class="property-group">
                <pre class="raw-json-content" style="
                    background: var(--bg-tertiary, #1a1a1a);
                    border: 1px solid var(--border-color, #333);
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 11px;
                    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                    overflow-x: auto;
                    max-height: 400px;
                    overflow-y: auto;
                    white-space: pre;
                    color: var(--text-secondary, #aaa);
                    margin: 0;
                ">${this.escapeHtml(jsonString)}</pre>
                <button class="copy-json-btn" onclick="navigator.clipboard.writeText(this.previousElementSibling.textContent).then(() => { this.textContent = 'Copied!'; setTimeout(() => this.textContent = 'Copy JSON', 1500); })" style="
                    margin-top: 8px;
                    padding: 4px 12px;
                    font-size: 11px;
                    background: var(--accent-primary, #4a9b7e);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                ">Copy JSON</button>
            </div>`;
        } else {
            html += `<div class="scitex-no-traces">
                No metadata available
            </div>`;
        }

        html += `</div></div>`;

        // EMBEDDED INFO section (fetches scitex metadata from actual image file)
        html += `<div class="scitex-section">
            <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); const content = this.nextElementSibling; content.style.display = this.classList.contains('collapsed') ? 'none' : 'block'; if (!this.classList.contains('collapsed')) { window.dispatchEvent(new CustomEvent('load-embedded-info')); }">
                <i class="fas fa-chevron-down"></i>
                <span>Embedded Info</span>
            </div>
            <div class="scitex-section-content" style="display: none;" id="embedded-info-content">
                <div class="scitex-no-traces" style="color: var(--text-muted, #666);">
                    <i class="fas fa-spinner fa-spin"></i> Click to load embedded metadata...
                </div>
            </div>
        </div>`;

        this.dynamicPropertiesEl.innerHTML = html;

        // Setup event listener for loading embedded info
        this.setupEmbeddedInfoLoader(obj);

        console.log('[PropertiesManager] Showing canvas object properties:', name);
    }

    /**
     * Setup embedded info loader for the current canvas object
     */
    private setupEmbeddedInfoLoader(obj: any): void {
        const handler = async () => {
            window.removeEventListener('load-embedded-info', handler);
            await this.loadEmbeddedInfo(obj);
        };
        window.addEventListener('load-embedded-info', handler);
    }

    /**
     * Load embedded metadata from the image via backend API
     */
    private async loadEmbeddedInfo(obj: any): Promise<void> {
        const contentEl = document.getElementById('embedded-info-content');
        if (!contentEl) return;

        // Show loading state
        contentEl.innerHTML = `<div class="scitex-no-traces" style="color: var(--text-muted, #666);">
            <i class="fas fa-spinner fa-spin"></i> Loading embedded metadata...
        </div>`;

        try {
            // Get base64 image data from the fabric object
            let imageData: string | null = null;

            if (obj.type === 'image' && obj._element) {
                // For fabric.Image objects, we need to preserve the original PNG metadata
                const src = obj._element.src;

                if (src && src.startsWith('data:')) {
                    // Already a data URL - use it directly
                    imageData = src;
                } else if (src && (src.startsWith('http') || src.startsWith('/'))) {
                    // URL to image file - fetch the original file to preserve PNG metadata
                    // Using toDataURL() would re-encode and lose the metadata chunks
                    try {
                        const response = await fetch(src);
                        const blob = await response.blob();
                        imageData = await new Promise<string>((resolve, reject) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result as string);
                            reader.onerror = reject;
                            reader.readAsDataURL(blob);
                        });
                    } catch (fetchError) {
                        console.warn('[PropertiesManager] Failed to fetch original image, falling back to toDataURL:', fetchError);
                        // Fallback to toDataURL (will lose metadata)
                        if (obj.toDataURL) {
                            imageData = obj.toDataURL({ format: 'png' });
                        }
                    }
                } else if (obj.toDataURL) {
                    // Fallback: convert to data URL (will lose PNG metadata chunks)
                    imageData = obj.toDataURL({ format: 'png' });
                }
            } else if (obj.toDataURL) {
                // Fallback: try to convert any object to data URL
                imageData = obj.toDataURL({ format: 'png' });
            }

            if (!imageData) {
                contentEl.innerHTML = `<div class="scitex-no-traces">
                    <i class="fas fa-exclamation-circle"></i> Cannot extract image data
                </div>`;
                return;
            }

            // Call the backend API to extract embedded metadata
            const response = await fetch('/vis/api/plot/metadata/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });

            const result = await response.json();

            if (!result.success) {
                contentEl.innerHTML = `<div class="scitex-no-traces">
                    <i class="fas fa-exclamation-circle"></i> ${result.error || 'Failed to extract metadata'}
                </div>`;
                return;
            }

            if (!result.has_metadata) {
                contentEl.innerHTML = `<div class="scitex-no-traces">
                    <i class="fas fa-info-circle"></i> No embedded scitex metadata found
                </div>`;
                return;
            }

            // Display the embedded metadata
            const metadata = result.metadata;
            let html = '';

            // Schema info
            if (metadata.scitex_schema) {
                html += `<div class="property-group">
                    <label class="property-label">Schema</label>
                    <input type="text" class="property-input" value="${metadata.scitex_schema}" readonly>
                </div>`;
            }

            if (metadata.scitex_schema_version) {
                html += `<div class="property-group">
                    <label class="property-label">Schema Version</label>
                    <input type="text" class="property-input" value="${metadata.scitex_schema_version}" readonly>
                </div>`;
            }

            // Runtime info
            if (metadata.runtime) {
                const rt = metadata.runtime;
                if (rt.scitex_version) {
                    html += `<div class="property-group">
                        <label class="property-label">SciTeX Version</label>
                        <input type="text" class="property-input" value="${rt.scitex_version}" readonly>
                    </div>`;
                }
                if (rt.created_at) {
                    html += `<div class="property-group">
                        <label class="property-label">Created At</label>
                        <input type="text" class="property-input" value="${rt.created_at}" readonly>
                    </div>`;
                }
            }

            // Figure info
            if (metadata.figure) {
                const fig = metadata.figure;
                if (fig.size_mm) {
                    const [w, h] = fig.size_mm;
                    html += `<div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">Width (mm)</label>
                            <input type="text" class="property-input" value="${w}" readonly>
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Height (mm)</label>
                            <input type="text" class="property-input" value="${h}" readonly>
                        </div>
                    </div>`;
                }
                if (fig.dpi) {
                    html += `<div class="property-group">
                        <label class="property-label">DPI</label>
                        <input type="text" class="property-input" value="${fig.dpi}" readonly>
                    </div>`;
                }
                if (fig.mode) {
                    html += `<div class="property-group">
                        <label class="property-label">Mode</label>
                        <input type="text" class="property-input" value="${fig.mode}" readonly>
                    </div>`;
                }
            }

            // Full JSON button
            html += `<div class="property-group" style="margin-top: 12px;">
                <button class="copy-json-btn" onclick="navigator.clipboard.writeText(JSON.stringify(${this.escapeHtml(JSON.stringify(metadata))}, null, 2)).then(() => { this.textContent = 'Copied!'; setTimeout(() => this.textContent = 'Copy Full Metadata', 1500); })" style="
                    padding: 4px 12px;
                    font-size: 11px;
                    background: var(--accent-secondary, #5a8bc7);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    width: 100%;
                ">Copy Full Metadata</button>
            </div>`;

            html += `<div class="scitex-no-traces" style="color: var(--accent-primary); font-style: normal; margin-top: 8px;">
                <i class="fas fa-check-circle"></i> SciTeX figure with embedded metadata
            </div>`;

            contentEl.innerHTML = html;

        } catch (error) {
            console.error('[PropertiesManager] Error loading embedded info:', error);
            contentEl.innerHTML = `<div class="scitex-no-traces">
                <i class="fas fa-exclamation-triangle"></i> Error: ${error}
            </div>`;
        }
    }

    /**
     * Escape HTML special characters for safe display
     */
    private escapeHtml(text: string): string {
        const map: Record<string, string> = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    /**
     * Show placeholder message when no object selected
     */
    public showNoSelection(): void {
        if (!this.dynamicPropertiesEl) return;

        this.dynamicPropertiesEl.innerHTML = `
            <div class="property-placeholder">
                Select an item to view properties
            </div>
        `;
    }

    /**
     * Show properties for a selected plot element (trace, scatter, bar, etc.)
     * Called when user clicks on a data element within a figure
     */
    public showElementProperties(elementName: string, elementInfo: any): void {
        if (!this.dynamicPropertiesEl || !this.selectedItemInfoEl) {
            console.warn('[PropertiesManager] Dynamic properties elements not found');
            return;
        }

        const label = elementInfo?.label || elementName;
        const elementType = elementInfo?.element_type || 'unknown';

        // Update header
        this.updateSelectedItemInfo('element', label);

        // Build properties HTML
        let html = '';

        // ELEMENT INFO section
        html += `<div class="scitex-section">
            <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                <i class="fas fa-chevron-down"></i>
                <span>Element Info</span>
            </div>
            <div class="scitex-section-content">`;

        html += `<div class="property-group">
            <label class="property-label">Label</label>
            <input type="text" class="property-input" value="${label}" readonly>
        </div>`;

        html += `<div class="property-group">
            <label class="property-label">Type</label>
            <input type="text" class="property-input" value="${this.formatElementType(elementType)}" readonly>
        </div>`;

        html += `<div class="property-group">
            <label class="property-label">Element ID</label>
            <input type="text" class="property-input" value="${elementName}" readonly>
        </div>`;

        html += `</div></div>`;

        // CSV COLUMNS section (if available)
        if (elementInfo?.csv_columns) {
            html += `<div class="scitex-section">
                <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Data Columns</span>
                </div>
                <div class="scitex-section-content">`;

            const csvCols = elementInfo.csv_columns;

            if (csvCols.x) {
                html += `<div class="property-group">
                    <label class="property-label">X Column</label>
                    <input type="text" class="property-input" value="${csvCols.x.name} (index: ${csvCols.x.index})" readonly>
                </div>`;
            }

            if (csvCols.y) {
                html += `<div class="property-group">
                    <label class="property-label">Y Column</label>
                    <input type="text" class="property-input" value="${csvCols.y.name} (index: ${csvCols.y.index})" readonly>
                </div>`;
            }

            html += `<div class="scitex-no-traces" style="color: var(--accent-primary); font-style: normal;">
                <i class="fas fa-link"></i> Linked to CSV data
            </div>`;

            html += `</div></div>`;
        }

        // BOUNDING BOX section
        if (elementInfo?.x0 !== undefined) {
            html += `<div class="scitex-section">
                <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Bounding Box</span>
                </div>
                <div class="scitex-section-content" style="display: none;">`;

            html += `<div class="property-row">
                <div class="property-group half">
                    <label class="property-label">x0</label>
                    <input type="text" class="property-input" value="${elementInfo.x0} px" readonly>
                </div>
                <div class="property-group half">
                    <label class="property-label">y0</label>
                    <input type="text" class="property-input" value="${elementInfo.y0} px" readonly>
                </div>
            </div>`;

            html += `<div class="property-row">
                <div class="property-group half">
                    <label class="property-label">x1</label>
                    <input type="text" class="property-input" value="${elementInfo.x1} px" readonly>
                </div>
                <div class="property-group half">
                    <label class="property-label">y1</label>
                    <input type="text" class="property-input" value="${elementInfo.y1} px" readonly>
                </div>
            </div>`;

            const width = elementInfo.x1 - elementInfo.x0;
            const height = elementInfo.y1 - elementInfo.y0;
            html += `<div class="property-row">
                <div class="property-group half">
                    <label class="property-label">Width</label>
                    <input type="text" class="property-input" value="${width} px" readonly>
                </div>
                <div class="property-group half">
                    <label class="property-label">Height</label>
                    <input type="text" class="property-input" value="${height} px" readonly>
                </div>
            </div>`;

            html += `</div></div>`;
        }

        this.dynamicPropertiesEl.innerHTML = html;
        console.log(`[PropertiesManager] Showing element properties: ${label} (${elementType})`);
    }

    /**
     * Format element type for display
     */
    private formatElementType(type: string): string {
        const typeMap: Record<string, string> = {
            'line': 'Line Plot',
            'scatter': 'Scatter Plot',
            'bar': 'Bar Chart',
            'hist': 'Histogram',
            'boxplot': 'Box Plot',
            'violin': 'Violin Plot',
            'fill': 'Fill Area',
            'panel': 'Plot Panel',
        };
        return typeMap[type] || type.charAt(0).toUpperCase() + type.slice(1);
    }
}
