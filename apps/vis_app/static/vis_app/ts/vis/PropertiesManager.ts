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
            'annotation': 'fa-sticky-note'
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
}
