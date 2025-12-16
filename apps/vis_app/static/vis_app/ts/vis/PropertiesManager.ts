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
import { getCSRFToken } from './canvas/CanvasSerializationUtils.ts';
import { PltzPropertiesBuilder } from './properties/PltzPropertiesBuilder.ts';
import { CanvasObjectPropertiesBuilder } from './properties/CanvasObjectPropertiesBuilder.ts';
import { ElementPropertiesBuilder } from './properties/ElementPropertiesBuilder.ts';

export class PropertiesManager {
    private currentPropertiesTab: string = 'plot';
    private csrfToken: string;

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
        this.csrfToken = getCSRFToken();
    }

    /**
     * Get CSRF token from cookies
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

        // Check if this is a bundle panel (pltz)
        if (obj.isBundlePanel && obj.pltzPath) {
            this.showPltzProperties(obj.pltzPath, obj.panelLabel || obj.panelId, obj);
            return;
        }

        const name = obj.name || obj.type || 'Object';

        // Update header
        this.updateSelectedItemInfo('figure', name);

        // Build properties HTML using CanvasObjectPropertiesBuilder
        const html = CanvasObjectPropertiesBuilder.buildCanvasObjectPropertiesHTML(obj);


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
                <button class="copy-json-btn" onclick="navigator.clipboard.writeText(JSON.stringify(${PropertiesHTMLBuilder.escapeHtml(JSON.stringify(metadata))}, null, 2)).then(() => { this.textContent = 'Copied!'; setTimeout(() => this.textContent = 'Copy Full Metadata', 1500); })" style="
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

        // Update header
        this.updateSelectedItemInfo('element', label);

        // Build properties HTML using ElementPropertiesBuilder
        const html = ElementPropertiesBuilder.buildElementPropertiesHTML(elementName, elementInfo);

        this.dynamicPropertiesEl.innerHTML = html;
        console.log(`[PropertiesManager] Showing element properties:`, label, elementInfo?.element_type || 'unknown');
    }


    // =========================================================================
    // Pltz Bundle Properties (for canvas bundle integration)
    // =========================================================================

    // Cache for pltz bundle data
    private pltzCache: Map<string, { spec: any; style: any; hash?: string }> = new Map();

    // Callback for panel refresh after property changes
    private panelRefreshCallback?: (pltzPath: string) => Promise<void>;

    // Debounce timers for auto-render per panel
    private renderDebounceTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

    // Track panels with pending changes (dirty flag)
    private dirtyPanels: Set<string> = new Set();

    // Debounce delay for auto-render (ms)
    // Auto-update interval in ms (configurable via dropdown)
    // 0 = Off, 500 = Hot, 1000 = Fast, 2000 = Normal, 5000 = Slow
    private autoUpdateInterval: number = 2000;

    // Current pltz path for statistics refresh
    private currentPltzPath: string | null = null;

    /**
     * Set callback for panel refresh after property changes
     */
    public setPanelRefreshCallback(callback: (pltzPath: string) => Promise<void>): void {
        this.panelRefreshCallback = callback;
    }

    /**
     * Show properties for a pltz bundle panel (Enhanced with Flask editor features)
     */
    public async showPltzProperties(pltzPath: string, panelLabel: string, obj: any): Promise<void> {
        if (!this.dynamicPropertiesEl || !this.selectedItemInfoEl) {
            console.warn('[PropertiesManager] Dynamic properties elements not found');
            return;
        }

        // Store current path for statistics refresh
        this.currentPltzPath = pltzPath;

        // Update header
        this.updateSelectedItemInfo('panel', `Panel ${panelLabel}`);

        // Show loading state
        this.dynamicPropertiesEl.innerHTML = `
            <div class="scitex-loading">
                <i class="fas fa-spinner fa-spin"></i> Loading pltz bundle...
            </div>`;

        try {
            // Fetch pltz bundle data
            const response = await fetch(`/vis/api/bundles/pltz/load/?path=${encodeURIComponent(pltzPath)}`);
            if (!response.ok) {
                throw new Error('Failed to load pltz bundle');
            }

            const pltzData = await response.json();
            const spec = pltzData.spec || {};
            const style = pltzData.style || {};

            // Cache the data
            this.pltzCache.set(pltzPath, { spec, style });

            // Build properties HTML with Flask editor sections
            let html = '';

            // ═══════════════════════════════════════════════════════════════
            // DIMENSIONS Section (Flask-style)
            // ═══════════════════════════════════════════════════════════════
            const sizeMm = style.size || {};
            html += `<div class="scitex-section">
                <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Dimensions</span>
                </div>
                <div class="scitex-section-content" style="display: none;">
                    <div class="property-group" style="margin-bottom: 8px;">
                        <label class="property-label">Unit</label>
                        <div class="unit-toggle" style="display: flex; gap: 4px;">
                            <button class="unit-btn active" id="unit-mm" onclick="window.pltzSetUnit?.('mm')" style="flex: 1; padding: 4px 8px; border: 1px solid var(--border-color, #444); border-radius: 4px; background: var(--primary-color, #0d6efd); color: #fff; cursor: pointer; font-size: 11px;">mm</button>
                            <button class="unit-btn" id="unit-inch" onclick="window.pltzSetUnit?.('inch')" style="flex: 1; padding: 4px 8px; border: 1px solid var(--border-color, #444); border-radius: 4px; background: var(--bg-tertiary, #333); color: var(--text-primary, #fff); cursor: pointer; font-size: 11px;">inch</button>
                        </div>
                    </div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label" id="width-label">Width (mm)</label>
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.size.width_mm"
                                id="pltz-width"
                                value="${sizeMm.width_mm || 80}"
                                step="1" min="10" max="300">
                        </div>
                        <div class="property-group half">
                            <label class="property-label" id="height-label">Height (mm)</label>
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.size.height_mm"
                                id="pltz-height"
                                value="${sizeMm.height_mm || 60}"
                                step="1" min="10" max="300">
                        </div>
                    </div>
                    <div class="property-group">
                        <label class="property-label">DPI</label>
                        <input type="number" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.dpi"
                            value="${style.dpi || 300}"
                            step="1" min="72" max="600">
                    </div>
                </div>
            </div>`;

            // ═══════════════════════════════════════════════════════════════
            // STYLE Section (Flask-style)
            // ═══════════════════════════════════════════════════════════════
            const theme = style.theme || {};
            html += `<div class="scitex-section">
                <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Style</span>
                </div>
                <div class="scitex-section-content" style="display: none;">
                    <div class="property-group" style="margin-bottom: 8px;">
                        <label class="checkbox-field" style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" class="pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.grid"
                                ${style.grid ? 'checked' : ''}>
                            <span style="font-size: 12px;">Show Grid</span>
                        </label>
                    </div>
                    <div class="property-group">
                        <label class="property-label">Label Size (pt)</label>
                        <input type="number" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.axis_fontsize"
                            value="${style.axis_fontsize || 7}"
                            step="1" min="4" max="16">
                    </div>
                    <div class="property-group">
                        <label class="property-label">Background</label>
                        <div class="bg-toggle" style="display: flex; gap: 4px; margin-top: 4px;">
                            <button class="bg-btn ${style.facecolor === '#ffffff' ? 'active' : ''}" onclick="window.pltzSetBackground?.('white')" style="flex: 1; padding: 6px; border: 1px solid var(--border-color, #444); border-radius: 4px; background: #fff; cursor: pointer; font-size: 10px; color: #000;">White</button>
                            <button class="bg-btn ${style.transparent !== false ? 'active' : ''}" onclick="window.pltzSetBackground?.('transparent')" style="flex: 1; padding: 6px; border: 1px solid var(--border-color, #444); border-radius: 4px; background: repeating-conic-gradient(#808080 0% 25%, transparent 0% 50%) 50% / 8px 8px; cursor: pointer; font-size: 10px; color: #fff; text-shadow: 0 0 2px #000;">Trans</button>
                            <button class="bg-btn ${style.facecolor === '#000000' ? 'active' : ''}" onclick="window.pltzSetBackground?.('black')" style="flex: 1; padding: 6px; border: 1px solid var(--border-color, #444); border-radius: 4px; background: #000; cursor: pointer; font-size: 10px; color: #fff;">Black</button>
                        </div>
                    </div>
                </div>
            </div>`;

            // ═══════════════════════════════════════════════════════════════
            // TITLE, LABELS & CAPTION Section (Flask-style)
            // ═══════════════════════════════════════════════════════════════
            const axes = spec.axes || [];
            const ax0 = axes[0] || {};
            const labels = ax0.labels || {};

            html += `<div class="scitex-section">
                <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Title, Labels & Caption</span>
                </div>
                <div class="scitex-section-content">
                    <div class="property-group">
                        <label class="property-label">Title</label>
                        <input type="text" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="spec.axes.0.labels.title"
                            value="${PropertiesHTMLBuilder.escapeHtml(labels.title || '')}"
                            placeholder="Plot title">
                    </div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">X Label</label>
                            <input type="text" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="spec.axes.0.labels.xlabel"
                                value="${PropertiesHTMLBuilder.escapeHtml(labels.xlabel || '')}"
                                placeholder="X axis">
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Y Label</label>
                            <input type="text" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="spec.axes.0.labels.ylabel"
                                value="${PropertiesHTMLBuilder.escapeHtml(labels.ylabel || '')}"
                                placeholder="Y axis">
                        </div>
                    </div>
                    <div class="property-group">
                        <label class="property-label">Caption</label>
                        <textarea class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="spec.caption"
                            rows="2"
                            placeholder="Figure caption..."
                            style="resize: vertical; min-height: 40px;">${PropertiesHTMLBuilder.escapeHtml(spec.caption || '')}</textarea>
                    </div>
                </div>
            </div>`;

            // ═══════════════════════════════════════════════════════════════
            // AXIS & TICKS Section (Flask-style with tabs)
            // ═══════════════════════════════════════════════════════════════
            const limits = ax0.limits || {};
            html += `<div class="scitex-section">
                <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Axis & Ticks</span>
                </div>
                <div class="scitex-section-content" style="display: none;">
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-muted, #888); margin-bottom: 6px;">Limits</div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">X Range</label>
                            <div style="display: flex; gap: 4px;">
                                <input type="number" class="property-input pltz-editable" style="width: 50%;"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="spec.axes.0.limits.xmin"
                                    value="${limits.xmin !== undefined ? limits.xmin : ''}"
                                    placeholder="Min" step="any">
                                <input type="number" class="property-input pltz-editable" style="width: 50%;"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="spec.axes.0.limits.xmax"
                                    value="${limits.xmax !== undefined ? limits.xmax : ''}"
                                    placeholder="Max" step="any">
                            </div>
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Y Range</label>
                            <div style="display: flex; gap: 4px;">
                                <input type="number" class="property-input pltz-editable" style="width: 50%;"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="spec.axes.0.limits.ymin"
                                    value="${limits.ymin !== undefined ? limits.ymin : ''}"
                                    placeholder="Min" step="any">
                                <input type="number" class="property-input pltz-editable" style="width: 50%;"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="spec.axes.0.limits.ymax"
                                    value="${limits.ymax !== undefined ? limits.ymax : ''}"
                                    placeholder="Max" step="any">
                            </div>
                        </div>
                    </div>
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-muted, #888); margin: 12px 0 6px 0;">Tick Settings</div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">X Ticks</label>
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.x_n_ticks"
                                value="${style.x_n_ticks || 5}"
                                step="1" min="2" max="15">
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Y Ticks</label>
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.y_n_ticks"
                                value="${style.y_n_ticks || 5}"
                                step="1" min="2" max="15">
                        </div>
                    </div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">Tick Direction</label>
                            <select class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.tick_direction">
                                <option value="out" ${style.tick_direction === 'out' ? 'selected' : ''}>Out</option>
                                <option value="in" ${style.tick_direction === 'in' ? 'selected' : ''}>In</option>
                                <option value="inout" ${style.tick_direction === 'inout' ? 'selected' : ''}>Both</option>
                            </select>
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Tick Font (pt)</label>
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.tick_fontsize"
                                value="${style.tick_fontsize || 7}"
                                step="1" min="4" max="16">
                        </div>
                    </div>
                    <div class="property-row" style="margin-top: 8px;">
                        <label class="checkbox-field" style="display: flex; align-items: center; gap: 6px; cursor: pointer; flex: 1;">
                            <input type="checkbox" class="pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.hide_top_spine"
                                ${style.hide_top_spine !== false ? 'checked' : ''}>
                            <span style="font-size: 11px;">Hide Top</span>
                        </label>
                        <label class="checkbox-field" style="display: flex; align-items: center; gap: 6px; cursor: pointer; flex: 1;">
                            <input type="checkbox" class="pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.hide_right_spine"
                                ${style.hide_right_spine !== false ? 'checked' : ''}>
                            <span style="font-size: 11px;">Hide Right</span>
                        </label>
                    </div>
                </div>
            </div>`;

            // ═══════════════════════════════════════════════════════════════
            // TRACES Section (Enhanced)
            // ═══════════════════════════════════════════════════════════════
            const traces = spec.traces || [];
            const traceStyles = style.traces || [];

            html += `<div class="scitex-section">
                <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Traces${traces.length > 0 ? ` (${traces.length})` : ''}</span>
                </div>
                <div class="scitex-section-content">`;

            if (traces.length > 0) {
                traces.forEach((trace: any, index: number) => {
                    const traceStyle = traceStyles.find((ts: any) => ts.trace_id === trace.id) || {};
                    const traceLabel = trace.label || trace.id || `Trace ${index + 1}`;

                    html += `<div class="trace-item" style="margin-bottom: 10px; padding: 8px; background: var(--bg-tertiary, #222); border-radius: 4px; border-left: 3px solid ${traceStyle.color || '#0080bf'};">
                        <div style="font-weight: 600; font-size: 11px; margin-bottom: 6px; color: var(--text-primary, #fff);">
                            ${PropertiesHTMLBuilder.escapeHtml(traceLabel)}
                        </div>
                        <div class="property-row">
                            <div class="property-group" style="flex: 0 0 50px;">
                                <label class="property-label">Color</label>
                                <input type="color" class="property-input pltz-editable"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="style.traces.${index}.color"
                                    data-trace-id="${trace.id}"
                                    value="${traceStyle.color || '#0080bf'}"
                                    style="height: 26px; padding: 1px; width: 100%;">
                            </div>
                            <div class="property-group" style="flex: 1;">
                                <label class="property-label">Width</label>
                                <input type="number" class="property-input pltz-editable"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="style.traces.${index}.linewidth"
                                    data-trace-id="${trace.id}"
                                    value="${traceStyle.linewidth || 1.5}"
                                    step="0.5" min="0.5" max="10">
                            </div>
                            <div class="property-group" style="flex: 1;">
                                <label class="property-label">Style</label>
                                <select class="property-input pltz-editable"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="style.traces.${index}.linestyle"
                                    data-trace-id="${trace.id}">
                                    <option value="-" ${traceStyle.linestyle === '-' || !traceStyle.linestyle ? 'selected' : ''}>Solid</option>
                                    <option value="--" ${traceStyle.linestyle === '--' ? 'selected' : ''}>Dashed</option>
                                    <option value="-." ${traceStyle.linestyle === '-.' ? 'selected' : ''}>Dash-dot</option>
                                    <option value=":" ${traceStyle.linestyle === ':' ? 'selected' : ''}>Dotted</option>
                                </select>
                            </div>
                        </div>
                        <div class="property-row" style="margin-top: 4px;">
                            <div class="property-group" style="flex: 1;">
                                <label class="property-label">Marker</label>
                                <select class="property-input pltz-editable"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="style.traces.${index}.marker"
                                    data-trace-id="${trace.id}">
                                    <option value="" ${!traceStyle.marker ? 'selected' : ''}>None</option>
                                    <option value="o" ${traceStyle.marker === 'o' ? 'selected' : ''}>Circle</option>
                                    <option value="s" ${traceStyle.marker === 's' ? 'selected' : ''}>Square</option>
                                    <option value="^" ${traceStyle.marker === '^' ? 'selected' : ''}>Triangle</option>
                                    <option value="D" ${traceStyle.marker === 'D' ? 'selected' : ''}>Diamond</option>
                                </select>
                            </div>
                            <div class="property-group" style="flex: 1;">
                                <label class="property-label">Alpha</label>
                                <input type="range" class="property-input pltz-editable"
                                    data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                    data-property="style.traces.${index}.alpha"
                                    data-trace-id="${trace.id}"
                                    value="${traceStyle.alpha || 1}"
                                    min="0" max="1" step="0.1"
                                    style="height: 20px;">
                            </div>
                        </div>
                    </div>`;
                });
            } else {
                html += `<div style="font-size: 11px; color: var(--text-muted, #888); font-style: italic; padding: 8px;">
                    Click on a trace in the preview to edit its properties.
                </div>`;
            }

            html += `</div></div>`;

            // ═══════════════════════════════════════════════════════════════
            // LEGEND Section (Enhanced)
            // ═══════════════════════════════════════════════════════════════
            const legend = style.legend || {};
            html += `<div class="scitex-section">
                <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Legend</span>
                </div>
                <div class="scitex-section-content" style="display: none;">
                    <div class="property-group" style="margin-bottom: 8px;">
                        <label class="checkbox-field" style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" class="pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.legend.visible"
                                ${legend.visible !== false ? 'checked' : ''}>
                            <span style="font-size: 12px;">Show Legend</span>
                        </label>
                    </div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">Position</label>
                            <select class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.legend.location">
                                <option value="best" ${legend.location === 'best' || !legend.location ? 'selected' : ''}>Best (auto)</option>
                                <option value="upper right" ${legend.location === 'upper right' ? 'selected' : ''}>Upper Right</option>
                                <option value="upper left" ${legend.location === 'upper left' ? 'selected' : ''}>Upper Left</option>
                                <option value="lower right" ${legend.location === 'lower right' ? 'selected' : ''}>Lower Right</option>
                                <option value="lower left" ${legend.location === 'lower left' ? 'selected' : ''}>Lower Left</option>
                                <option value="center right" ${legend.location === 'center right' ? 'selected' : ''}>Center Right</option>
                                <option value="center left" ${legend.location === 'center left' ? 'selected' : ''}>Center Left</option>
                            </select>
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Columns</label>
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.legend.ncols"
                                value="${legend.ncols || 1}"
                                step="1" min="1" max="5">
                        </div>
                    </div>
                    <div class="property-row" style="margin-top: 6px;">
                        <label class="checkbox-field" style="display: flex; align-items: center; gap: 6px; cursor: pointer; flex: 1;">
                            <input type="checkbox" class="pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.legend.frameon"
                                ${legend.frameon ? 'checked' : ''}>
                            <span style="font-size: 11px;">Show Frame</span>
                        </label>
                        <div class="property-group" style="flex: 1;">
                            <label class="property-label">Font (pt)</label>
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="style.legend.fontsize"
                                value="${legend.fontsize || 6}"
                                step="1" min="4" max="16">
                        </div>
                    </div>
                </div>
            </div>`;

            // ═══════════════════════════════════════════════════════════════
            // STATISTICS Section (Flask-style - NEW!)
            // ═══════════════════════════════════════════════════════════════
            html += `<div class="scitex-section">
                <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                    <i class="fas fa-chevron-down"></i>
                    <span>Statistics</span>
                </div>
                <div class="scitex-section-content">
                    <div id="pltz-stats-container" style="font-size: 11px;">
                        <div class="stats-loading" style="color: var(--text-muted, #888); font-style: italic;">
                            <i class="fas fa-spinner fa-spin"></i> Loading statistics...
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-sm" id="pltz-refresh-stats-btn" style="width: 100%; margin-top: 8px;">
                        <i class="fas fa-chart-bar"></i> Refresh Stats
                    </button>
                </div>
            </div>`;

            // ═══════════════════════════════════════════════════════════════
            // ANNOTATIONS Section (text overlays, arrows, labels)
            // ═══════════════════════════════════════════════════════════════
            html += `<div class="scitex-section">
                <div class="scitex-section-header scitex-section-toggle collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.classList.toggle('collapsed');">
                    <i class="fas fa-chevron-right"></i>
                    <span>Annotations</span>
                </div>
                <div class="scitex-section-content collapsed">
                    <div class="property-group" style="margin-bottom: 8px;">
                        <label class="property-label">Text</label>
                        <input type="text" class="property-input" id="pltz-annot-text" placeholder="Annotation text">
                    </div>
                    <div class="property-row">
                        <div class="property-group" style="flex: 1;">
                            <label class="property-label">X (0-1)</label>
                            <input type="number" class="property-input" id="pltz-annot-x" value="0.5" min="0" max="1" step="0.05" style="font-size: 11px;">
                        </div>
                        <div class="property-group" style="flex: 1;">
                            <label class="property-label">Y (0-1)</label>
                            <input type="number" class="property-input" id="pltz-annot-y" value="0.5" min="0" max="1" step="0.05" style="font-size: 11px;">
                        </div>
                        <div class="property-group" style="flex: 1;">
                            <label class="property-label">Size</label>
                            <input type="number" class="property-input" id="pltz-annot-size" value="10" min="4" max="24" step="1" style="font-size: 11px;">
                        </div>
                    </div>
                    <div class="property-row" style="margin-top: 8px;">
                        <div class="property-group" style="flex: 1;">
                            <label class="property-label">Color</label>
                            <input type="color" class="property-color" id="pltz-annot-color" value="#000000">
                        </div>
                        <div class="property-group" style="flex: 1;">
                            <label class="property-label">Weight</label>
                            <select class="property-input" id="pltz-annot-weight" style="font-size: 11px;">
                                <option value="normal">Normal</option>
                                <option value="bold">Bold</option>
                            </select>
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-sm" id="pltz-add-annotation-btn" style="width: 100%; margin-top: 8px;">
                        <i class="fas fa-plus"></i> Add Annotation
                    </button>
                    <div id="pltz-annotations-list" style="margin-top: 8px; font-size: 11px;"></div>
                </div>
            </div>`;

            // ═══════════════════════════════════════════════════════════════
            // ACTIONS Section (Flask-style with Auto-Update dropdown)
            // ═══════════════════════════════════════════════════════════════
            html += `<div class="scitex-section">
                <div class="scitex-section-header">Actions</div>
                <div class="scitex-section-content" style="padding-top: 4px;">
                    <div id="pltz-status" class="pltz-status" style="
                        font-size: 11px;
                        padding: 6px 8px;
                        margin-bottom: 8px;
                        border-radius: 4px;
                        display: none;
                        text-align: center;
                    "></div>
                    <div class="property-row" style="align-items: flex-end; margin-bottom: 8px;">
                        <div class="property-group" style="flex: 1;">
                            <label class="property-label">Auto-Update</label>
                            <select class="property-input" id="pltz-auto-update-interval" style="font-size: 11px;">
                                <option value="0">Off</option>
                                <option value="500">Hot (0.5s)</option>
                                <option value="1000">Fast (1s)</option>
                                <option value="2000" selected>Normal (2s)</option>
                                <option value="5000">Slow (5s)</option>
                            </select>
                        </div>
                        <button class="btn btn-cta btn-sm" id="pltz-update-now-btn" style="flex: 0; margin-left: 8px; white-space: nowrap;">
                            Update Now
                        </button>
                    </div>
                    <button class="btn btn-primary btn-sm" id="pltz-save-btn" style="width: 100%; margin-bottom: 6px;">
                        <i class="fas fa-save"></i> Save
                    </button>
                    <button class="btn btn-secondary btn-sm" id="pltz-reset-btn" style="width: 100%;">
                        <i class="fas fa-undo"></i> Reset
                    </button>
                </div>
            </div>`;

            this.dynamicPropertiesEl.innerHTML = html;

            // Setup event listeners for editable properties
            this.setupPltzPropertyListeners(pltzPath);

            // Setup auto-update dropdown
            this.setupAutoUpdateDropdown();

            // Setup annotations
            this.setupAnnotationsSection(pltzPath, spec?.annotations || []);

            // Load statistics
            this.loadPltzStatistics(pltzPath);

            console.log('[PropertiesManager] Showing enhanced pltz properties:', panelLabel, pltzPath);

        } catch (error) {
            console.error('[PropertiesManager] Failed to load pltz properties:', error);
            this.dynamicPropertiesEl.innerHTML = `
                <div class="scitex-error" style="color: var(--danger-color, #dc3545); padding: 12px;">
                    <i class="fas fa-exclamation-triangle"></i> Failed to load pltz bundle
                </div>`;
        }
    }

    /**
     * Setup auto-update dropdown event listener
     */
    private setupAutoUpdateDropdown(): void {
        const dropdown = document.getElementById('pltz-auto-update-interval') as HTMLSelectElement;
        if (dropdown) {
            // Set current value
            dropdown.value = String(this.autoUpdateInterval);

            dropdown.addEventListener('change', () => {
                this.autoUpdateInterval = parseInt(dropdown.value, 10);
                console.log(`[PropertiesManager] Auto-update interval set to: ${this.autoUpdateInterval}ms`);
            });
        }

        // Setup Update Now button
        const updateNowBtn = document.getElementById('pltz-update-now-btn');
        if (updateNowBtn && this.currentPltzPath) {
            updateNowBtn.addEventListener('click', async () => {
                if (this.currentPltzPath) {
                    await this.renderAndRefreshPanel(this.currentPltzPath);
                }
            });
        }

        // Setup Save button
        const saveBtn = document.getElementById('pltz-save-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                // Save is automatic, just show confirmation
                this.updateRenderStatus('success');
                setTimeout(() => this.updateRenderStatus('idle'), 2000);
            });
        }

        // Setup Reset button
        const resetBtn = document.getElementById('pltz-reset-btn');
        if (resetBtn && this.currentPltzPath) {
            resetBtn.addEventListener('click', async () => {
                if (this.currentPltzPath) {
                    // Clear cache and reload
                    this.pltzCache.delete(this.currentPltzPath);
                    // Re-fetch will happen on next selection
                    console.log('[PropertiesManager] Reset pltz bundle');
                }
            });
        }
    }

    /**
     * Setup annotations section event handlers
     */
    private setupAnnotationsSection(pltzPath: string, existingAnnotations: any[]): void {
        const addBtn = document.getElementById('pltz-add-annotation-btn');
        const listEl = document.getElementById('pltz-annotations-list');

        if (!addBtn || !listEl) return;

        // Track annotations locally
        const annotations = [...existingAnnotations];

        // Render existing annotations
        this.renderAnnotationsList(listEl, annotations, pltzPath);

        // Add annotation button handler
        addBtn.addEventListener('click', async () => {
            const textInput = document.getElementById('pltz-annot-text') as HTMLInputElement;
            const xInput = document.getElementById('pltz-annot-x') as HTMLInputElement;
            const yInput = document.getElementById('pltz-annot-y') as HTMLInputElement;
            const sizeInput = document.getElementById('pltz-annot-size') as HTMLInputElement;
            const colorInput = document.getElementById('pltz-annot-color') as HTMLInputElement;
            const weightSelect = document.getElementById('pltz-annot-weight') as HTMLSelectElement;

            const text = textInput?.value?.trim();
            if (!text) {
                console.warn('[PropertiesManager] Annotation text is empty');
                return;
            }

            const annotation = {
                id: `annot_${Date.now()}`,
                text: text,
                x: parseFloat(xInput?.value || '0.5'),
                y: parseFloat(yInput?.value || '0.5'),
                fontsize: parseInt(sizeInput?.value || '10'),
                color: colorInput?.value || '#000000',
                fontweight: weightSelect?.value || 'normal'
            };

            annotations.push(annotation);

            // Update spec with new annotation
            await this.updatePltzProperty(pltzPath, 'annotations', annotations);

            // Re-render list
            this.renderAnnotationsList(listEl, annotations, pltzPath);

            // Clear input
            textInput.value = '';

            console.log('[PropertiesManager] Added annotation:', annotation);
        });
    }

    /**
     * Render annotations list with delete buttons
     */
    private renderAnnotationsList(container: HTMLElement, annotations: any[], pltzPath: string): void {
        if (annotations.length === 0) {
            container.innerHTML = '<div style="color: var(--text-muted, #888); font-style: italic;">No annotations</div>';
            return;
        }

        container.innerHTML = annotations.map((annot, idx) => `
            <div class="annotation-item" style="
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 8px;
                background: var(--bg-tertiary, #222);
                border-radius: 4px;
                margin-bottom: 4px;
            ">
                <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    "${annot.text}" (${annot.x?.toFixed(2)}, ${annot.y?.toFixed(2)})
                </span>
                <button class="annotation-delete-btn" data-idx="${idx}" style="
                    background: none;
                    border: none;
                    color: var(--danger-color, #dc3545);
                    cursor: pointer;
                    padding: 2px 4px;
                    font-size: 12px;
                ">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');

        // Attach delete handlers
        container.querySelectorAll('.annotation-delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const idx = parseInt((btn as HTMLElement).dataset.idx || '-1');
                if (idx >= 0) {
                    annotations.splice(idx, 1);
                    await this.updatePltzProperty(pltzPath, 'annotations', annotations);
                    this.renderAnnotationsList(container, annotations, pltzPath);
                    console.log('[PropertiesManager] Removed annotation at index:', idx);
                }
            });
        });
    }

    /**
     * Load statistics for pltz bundle
     */
    private async loadPltzStatistics(pltzPath: string): Promise<void> {
        const container = document.getElementById('pltz-stats-container');
        if (!container) return;

        try {
            // Fetch statistics from API
            const response = await fetch(`/vis/api/bundles/pltz/stats/?path=${encodeURIComponent(pltzPath)}`);

            if (!response.ok) {
                // API might not exist yet, show placeholder
                container.innerHTML = `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
                        <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                            <div style="color: var(--text-muted, #888); font-size: 10px;">N points</div>
                            <div style="font-weight: 600;">-</div>
                        </div>
                        <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                            <div style="color: var(--text-muted, #888); font-size: 10px;">Mean</div>
                            <div style="font-weight: 600;">-</div>
                        </div>
                        <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                            <div style="color: var(--text-muted, #888); font-size: 10px;">Std</div>
                            <div style="font-weight: 600;">-</div>
                        </div>
                        <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                            <div style="color: var(--text-muted, #888); font-size: 10px;">Range</div>
                            <div style="font-weight: 600;">-</div>
                        </div>
                    </div>
                    <div style="font-size: 10px; color: var(--text-muted, #666); margin-top: 6px; font-style: italic;">
                        Statistics API not available
                    </div>`;
                return;
            }

            const stats = await response.json();
            this.renderStatistics(container, stats);

        } catch (error) {
            console.warn('[PropertiesManager] Failed to load statistics:', error);
            container.innerHTML = `
                <div style="color: var(--text-muted, #888); font-style: italic; font-size: 11px;">
                    Unable to load statistics
                </div>`;
        }

        // Setup refresh stats button
        const refreshBtn = document.getElementById('pltz-refresh-stats-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                if (this.currentPltzPath) {
                    this.loadPltzStatistics(this.currentPltzPath);
                }
            });
        }
    }

    /**
     * Render statistics in container
     */
    private renderStatistics(container: HTMLElement, stats: any): void {
        const formatNum = (n: number | undefined) => n !== undefined ? n.toFixed(3) : '-';

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px;">
                <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                    <div style="color: var(--text-muted, #888); font-size: 10px;">N points</div>
                    <div style="font-weight: 600;">${stats.n || '-'}</div>
                </div>
                <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                    <div style="color: var(--text-muted, #888); font-size: 10px;">Mean</div>
                    <div style="font-weight: 600;">${formatNum(stats.mean)}</div>
                </div>
                <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                    <div style="color: var(--text-muted, #888); font-size: 10px;">Std</div>
                    <div style="font-weight: 600;">${formatNum(stats.std)}</div>
                </div>
                <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                    <div style="color: var(--text-muted, #888); font-size: 10px;">Min</div>
                    <div style="font-weight: 600;">${formatNum(stats.min)}</div>
                </div>
                <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                    <div style="color: var(--text-muted, #888); font-size: 10px;">Max</div>
                    <div style="font-weight: 600;">${formatNum(stats.max)}</div>
                </div>
                <div style="background: var(--bg-tertiary, #222); padding: 6px 8px; border-radius: 4px;">
                    <div style="color: var(--text-muted, #888); font-size: 10px;">Range</div>
                    <div style="font-weight: 600;">${formatNum(stats.range)}</div>
                </div>
            </div>`;
    }

    /**
     * Setup event listeners for pltz property inputs
     */
    private setupPltzPropertyListeners(pltzPath: string): void {
        const editables = this.dynamicPropertiesEl?.querySelectorAll('.pltz-editable');
        if (!editables) return;

        editables.forEach(input => {
            input.addEventListener('change', async (e) => {
                const target = e.target as HTMLInputElement | HTMLSelectElement;
                const property = target.dataset.property;
                const value = target.type === 'checkbox'
                    ? (target as HTMLInputElement).checked
                    : target.value;

                if (!property) return;

                await this.updatePltzProperty(pltzPath, property, value);
            });
        });

        // Setup refresh button
        const refreshBtn = this.dynamicPropertiesEl?.querySelector('#pltz-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                await this.renderAndRefreshPanel(pltzPath);
            });
        }
    }

    /**
     * Update a pltz bundle property
     */
    private async updatePltzProperty(pltzPath: string, property: string, value: any): Promise<void> {
        console.log(`[PropertiesManager] Updating pltz property: ${property} = ${value}`);

        // Parse the property path
        const [type, ...pathParts] = property.split('.');
        if (type !== 'spec' && type !== 'style') {
            console.warn('[PropertiesManager] Invalid property type:', type);
            return;
        }

        // Get cached data
        const cached = this.pltzCache.get(pltzPath);
        if (!cached) {
            console.warn('[PropertiesManager] No cached data for:', pltzPath);
            return;
        }

        // Build update payload
        const updateData: any = { path: pltzPath };

        // Update the cached data
        let obj = type === 'spec' ? cached.spec : cached.style;
        for (let i = 0; i < pathParts.length - 1; i++) {
            const key = pathParts[i];
            if (obj[key] === undefined) {
                obj[key] = isNaN(Number(pathParts[i + 1])) ? {} : [];
            }
            obj = obj[key];
        }
        const lastKey = pathParts[pathParts.length - 1];

        // Parse value if needed
        let parsedValue = value;
        if (value === 'true') parsedValue = true;
        else if (value === 'false') parsedValue = false;
        else if (!isNaN(Number(value)) && value !== '') parsedValue = Number(value);

        obj[lastKey] = parsedValue;

        // Send update to server
        updateData[type] = type === 'spec' ? cached.spec : cached.style;

        try {
            const response = await fetch('/vis/api/bundles/pltz/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                },
                body: JSON.stringify(updateData),
            });

            if (!response.ok) {
                throw new Error('Failed to update pltz bundle');
            }

            console.log('[PropertiesManager] Pltz property updated successfully');

            // Mark panel as dirty and schedule debounced auto-render
            this.dirtyPanels.add(pltzPath);
            this.showPendingStatus();
            this.scheduleAutoRender(pltzPath);

        } catch (error) {
            console.error('[PropertiesManager] Failed to update pltz property:', error);
        }
    }

    /**
     * Schedule debounced auto-render for a panel
     * Waits for AUTO_RENDER_DEBOUNCE_MS after last change before rendering
     */
    private scheduleAutoRender(pltzPath: string): void {
        // Clear existing timer for this panel
        const existingTimer = this.renderDebounceTimers.get(pltzPath);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        // If auto-update is off, don't schedule render
        if (this.autoUpdateInterval === 0) {
            console.log('[PropertiesManager] Auto-update is off, skipping scheduled render');
            return;
        }

        // Schedule new render
        const timer = setTimeout(async () => {
            if (this.dirtyPanels.has(pltzPath)) {
                console.log(`[PropertiesManager] Auto-rendering panel after edits: ${pltzPath}`);
                await this.renderAndRefreshPanel(pltzPath);
                this.dirtyPanels.delete(pltzPath);
            }
            this.renderDebounceTimers.delete(pltzPath);
        }, this.autoUpdateInterval);

        this.renderDebounceTimers.set(pltzPath, timer);
    }

    /**
     * Cancel pending auto-render for a panel (e.g., when panel is deselected)
     */
    public cancelPendingRender(pltzPath?: string): void {
        if (pltzPath) {
            const timer = this.renderDebounceTimers.get(pltzPath);
            if (timer) {
                clearTimeout(timer);
                this.renderDebounceTimers.delete(pltzPath);
            }
            this.dirtyPanels.delete(pltzPath);
        } else {
            // Cancel all pending renders
            this.renderDebounceTimers.forEach(timer => clearTimeout(timer));
            this.renderDebounceTimers.clear();
            this.dirtyPanels.clear();
        }
    }

    /**
     * Check if a panel has pending changes
     */
    public isPanelDirty(pltzPath: string): boolean {
        return this.dirtyPanels.has(pltzPath);
    }

    /**
     * Re-render pltz bundle and refresh canvas panel
     */
    private async renderAndRefreshPanel(pltzPath: string): Promise<void> {
        console.log('[PropertiesManager] Re-rendering panel:', pltzPath);

        // Show rendering status
        this.updateRenderStatus('rendering');

        try {
            // Call render API
            const response = await fetch(`/vis/api/bundles/pltz/render/?path=${encodeURIComponent(pltzPath)}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                },
            });

            if (!response.ok) {
                throw new Error('Failed to render pltz bundle');
            }

            // Call panel refresh callback if set
            if (this.panelRefreshCallback) {
                await this.panelRefreshCallback(pltzPath);
            }

            console.log('[PropertiesManager] Panel re-rendered successfully');

            // Show success status briefly
            this.updateRenderStatus('success');
            setTimeout(() => this.updateRenderStatus('idle'), 2000);

        } catch (error) {
            console.error('[PropertiesManager] Failed to re-render panel:', error);
            this.updateRenderStatus('error');
            setTimeout(() => this.updateRenderStatus('idle'), 3000);
        }
    }

    /**
     * Update render status UI
     */
    private updateRenderStatus(status: 'idle' | 'pending' | 'rendering' | 'success' | 'error'): void {
        const statusEl = document.getElementById('pltz-status');
        const refreshBtn = document.getElementById('pltz-refresh-btn');
        const refreshIcon = document.getElementById('pltz-refresh-icon');
        const refreshText = document.getElementById('pltz-refresh-text');

        if (!statusEl) return;

        switch (status) {
            case 'idle':
                statusEl.style.display = 'none';
                if (refreshBtn) refreshBtn.removeAttribute('disabled');
                if (refreshIcon) refreshIcon.className = 'fas fa-sync-alt';
                if (refreshText) refreshText.textContent = 'Re-render Panel';
                break;

            case 'pending':
                statusEl.style.display = 'block';
                statusEl.style.background = 'var(--warning-bg, #3d3d00)';
                statusEl.style.color = 'var(--warning-color, #ffc107)';
                statusEl.innerHTML = '<i class="fas fa-clock"></i> Changes pending...';
                break;

            case 'rendering':
                statusEl.style.display = 'block';
                statusEl.style.background = 'var(--info-bg, #1a3a4a)';
                statusEl.style.color = 'var(--info-color, #17a2b8)';
                statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rendering...';
                if (refreshBtn) refreshBtn.setAttribute('disabled', 'true');
                if (refreshIcon) refreshIcon.className = 'fas fa-spinner fa-spin';
                if (refreshText) refreshText.textContent = 'Rendering...';
                break;

            case 'success':
                statusEl.style.display = 'block';
                statusEl.style.background = 'var(--success-bg, #1a3d1a)';
                statusEl.style.color = 'var(--success-color, #28a745)';
                statusEl.innerHTML = '<i class="fas fa-check-circle"></i> Updated';
                if (refreshBtn) refreshBtn.removeAttribute('disabled');
                if (refreshIcon) refreshIcon.className = 'fas fa-sync-alt';
                if (refreshText) refreshText.textContent = 'Re-render Panel';
                break;

            case 'error':
                statusEl.style.display = 'block';
                statusEl.style.background = 'var(--danger-bg, #3d1a1a)';
                statusEl.style.color = 'var(--danger-color, #dc3545)';
                statusEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Render failed';
                if (refreshBtn) refreshBtn.removeAttribute('disabled');
                if (refreshIcon) refreshIcon.className = 'fas fa-sync-alt';
                if (refreshText) refreshText.textContent = 'Retry Render';
                break;
        }
    }

    /**
     * Show pending status when edits are made
     */
    private showPendingStatus(): void {
        this.updateRenderStatus('pending');
    }
}
