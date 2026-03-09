/**
 * Gallery Manager
 * Coordinates gallery UI and data management
 */

import { GalleryData } from './GalleryData';
import { GalleryUI } from './GalleryUI';

export class GalleryManager {
    private galleryData: GalleryData;
    private galleryUI: GalleryUI;
    private updateStatusCallback?: (message: string) => void;

    constructor(callbacks: {
        updateStatus?: (message: string) => void;
        getCanvas?: () => any;
        saveHistory?: () => void;
    }) {
        this.updateStatusCallback = callbacks.updateStatus;
        this.galleryData = new GalleryData(callbacks);
        this.galleryUI = new GalleryUI(this.galleryData);
    }

    /**
     * Setup the plot gallery panel
     */
    public async setupGalleryPanel(): Promise<void> {
        await this.galleryUI.setupGalleryPanel();
    }

    /**
     * Setup plot type dropdowns for plot buttons
     */
    public async setupPlotTypeDropdowns(): Promise<void> {
        try {
            // Load plot templates
            const plotData = await this.galleryData.loadPlotTemplates();
            if (!plotData) return;

            // Group plots by base type
            const plotGroups = this.galleryData.groupPlotsByType();

            // Create dropdown for each plot type button
            const plotButtons = document.querySelectorAll('.plot-type-btn');
            let currentOpenDropdown: HTMLElement | null = null;

            plotButtons.forEach(btn => {
                const plotType = (btn as HTMLElement).dataset.plotType;
                if (!plotType || plotType === 'more') return;

                const plots = plotGroups[plotType];
                if (!plots || plots.length === 0) return;

                // Create dropdown element
                const dropdown = document.createElement('div');
                dropdown.className = 'plot-type-dropdown';
                dropdown.dataset.type = plotType;

                const header = document.createElement('div');
                header.className = 'plot-type-dropdown-header';
                header.textContent = 'Select ' + (btn as HTMLElement).textContent?.trim() + ' Type';

                const grid = document.createElement('div');
                grid.className = 'plot-type-dropdown-grid';

                // Add plot items to grid
                plots.forEach((plot: any) => {
                    const item = document.createElement('div');
                    item.className = 'plot-type-dropdown-item';
                    item.dataset.plotKey = plot.key;

                    const badge = document.createElement('div');
                    badge.className = 'plot-type-dropdown-item-category';
                    badge.textContent = plot.category;

                    const imgContainer = document.createElement('div');
                    imgContainer.className = 'plot-type-dropdown-item-img';

                    const img = document.createElement('img');
                    img.src = '/static/vis_app/img/plot_gallery/' + plot.category + '/' + plot.thumbnail;
                    img.alt = plot.name;

                    const label = document.createElement('div');
                    label.className = 'plot-type-dropdown-item-label';
                    label.textContent = plot.name;

                    imgContainer.appendChild(img);
                    item.appendChild(badge);
                    item.appendChild(imgContainer);
                    item.appendChild(label);

                    // Click handler to select plot
                    item.addEventListener('click', () => {
                        // Update selection
                        grid.querySelectorAll('.plot-type-dropdown-item').forEach(i => i.classList.remove('selected'));
                        item.classList.add('selected');

                        // Set the plot type for rendering
                        console.log('[GalleryManager] Selected plot:', plot.key, plot);

                        // Close dropdown after selection
                        setTimeout(() => {
                            dropdown.classList.remove('show');
                            (btn as HTMLElement).classList.remove('has-dropdown-open');
                            currentOpenDropdown = null;
                        }, 200);

                        // TODO: Update plot configuration with selected type
                        this.updateStatusCallback?.('Selected: ' + plot.name);
                    });

                    grid.appendChild(item);
                });

                dropdown.appendChild(header);
                dropdown.appendChild(grid);
                document.body.appendChild(dropdown);

                // Toggle dropdown on button click
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();

                    // Close any open dropdown
                    if (currentOpenDropdown && currentOpenDropdown !== dropdown) {
                        currentOpenDropdown.classList.remove('show');
                        document.querySelectorAll('.plot-type-btn').forEach(b => b.classList.remove('has-dropdown-open'));
                    }

                    // Toggle this dropdown
                    const isOpen = dropdown.classList.contains('show');
                    dropdown.classList.toggle('show');
                    (btn as HTMLElement).classList.toggle('has-dropdown-open');

                    if (!isOpen) {
                        // Position dropdown below button
                        const rect = (btn as HTMLElement).getBoundingClientRect();
                        const dropdownWidth = 360;
                        const left = rect.left + (rect.width / 2) - (dropdownWidth / 2);
                        const finalLeft = left < 10 ? 10 : (left + dropdownWidth > window.innerWidth - 10 ? window.innerWidth - dropdownWidth - 10 : left);

                        dropdown.style.left = finalLeft + 'px';
                        dropdown.style.top = rect.bottom + 'px';
                        dropdown.style.minWidth = dropdownWidth + 'px';
                        currentOpenDropdown = dropdown;
                    } else {
                        currentOpenDropdown = null;
                    }
                });
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (currentOpenDropdown && !(e.target as HTMLElement).closest('.plot-type-dropdown')) {
                    currentOpenDropdown.classList.remove('show');
                    document.querySelectorAll('.plot-type-btn').forEach(b => b.classList.remove('has-dropdown-open'));
                    currentOpenDropdown = null;
                }
            });

            console.log('[GalleryManager] Plot type dropdowns initialized');

        } catch (error) {
            console.error('[GalleryManager] Failed to setup plot dropdowns:', error);
        }
    }
}
