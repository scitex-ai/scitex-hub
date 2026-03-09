/**
 * Gallery UI Manager
 * Handles gallery panel UI, thumbnails, and user interactions
 */

import { GalleryData } from './GalleryData';

export class GalleryUI {
    private galleryData: GalleryData;
    private gallerySelectedPlotType: string | null = null;

    constructor(galleryData: GalleryData) {
        this.galleryData = galleryData;
    }

    /**
     * Setup the plot gallery panel with tabs and event handlers
     */
    public async setupGalleryPanel(): Promise<void> {
        console.log('[GalleryUI] Setting up plot gallery panel');

        try {
            // Load plot templates
            const plotData = await this.galleryData.loadPlotTemplates();
            if (!plotData) return;

            let currentCategory = 'basic';

            // Gallery toggle button
            const galleryToggle = document.getElementById('plot-gallery-toggle');
            const galleryDropdown = document.getElementById('plot-gallery-dropdown');

            if (galleryToggle && galleryDropdown) {
                galleryToggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const isOpen = galleryDropdown.style.display === 'block';

                    if (isOpen) {
                        galleryDropdown.style.display = 'none';
                        galleryToggle.classList.remove('active');
                    } else {
                        galleryDropdown.style.display = 'block';
                        galleryToggle.classList.add('active');
                        // Load thumbnails on first open if not already loaded
                        if (!galleryDropdown.dataset.loaded) {
                            this.loadGalleryThumbnails('basic');
                            galleryDropdown.dataset.loaded = 'true';
                        }
                    }
                });

                // Close dropdown when clicking outside
                document.addEventListener('click', (e) => {
                    if (!galleryDropdown.contains(e.target as Node) &&
                        e.target !== galleryToggle &&
                        !galleryToggle.contains(e.target as Node)) {
                        galleryDropdown.style.display = 'none';
                        galleryToggle.classList.remove('active');
                    }
                });
            }

            // Gallery tabs - switch category
            const galleryTabs = document.querySelectorAll('.gallery-tab');
            galleryTabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    const category = (e.currentTarget as HTMLElement).dataset.category;
                    if (!category) return;

                    // Update active tab
                    galleryTabs.forEach(t => t.classList.remove('active'));
                    (e.currentTarget as HTMLElement).classList.add('active');

                    // Load thumbnails for this category
                    currentCategory = category;
                    this.loadGalleryThumbnails(category);
                });
            });

            // Close button for info panel
            const closeBtn = document.querySelector('.gallery-info-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    const infoPanel = document.getElementById('gallery-info');
                    if (infoPanel) {
                        infoPanel.style.display = 'none';
                    }
                    this.gallerySelectedPlotType = null;
                    // Clear selected state from thumbnails
                    document.querySelectorAll('.gallery-thumbnail').forEach(thumb => {
                        thumb.classList.remove('selected');
                    });
                });
            }

            // "Add to Canvas" button
            const useBtn = document.getElementById('gallery-use-btn');
            if (useBtn) {
                useBtn.addEventListener('click', () => {
                    if (this.gallerySelectedPlotType) {
                        this.galleryData.addPlotToCanvas(this.gallerySelectedPlotType);

                        // Close dropdown and info panel after adding
                        if (galleryDropdown && galleryToggle) {
                            galleryDropdown.style.display = 'none';
                            galleryToggle.classList.remove('active');
                        }
                        const infoPanel = document.getElementById('gallery-info');
                        if (infoPanel) {
                            infoPanel.style.display = 'none';
                        }
                        this.gallerySelectedPlotType = null;
                        document.querySelectorAll('.gallery-thumbnail').forEach(thumb => {
                            thumb.classList.remove('selected');
                        });
                    }
                });
            }

        } catch (error) {
            console.error('[GalleryUI] Error setting up gallery panel:', error);
        }
    }

    /**
     * Load and display thumbnails for a specific category
     */
    private loadGalleryThumbnails(category: string): void {
        const thumbnailsContainer = document.getElementById('gallery-thumbnails');
        if (!thumbnailsContainer) return;

        // Clear existing thumbnails
        thumbnailsContainer.innerHTML = '';

        // Filter plot types by category
        const plotTypes = this.galleryData.filterByCategory(category);

        // Create thumbnail for each plot type
        plotTypes.forEach(([plotType, data]: [string, any]) => {
            const thumb = document.createElement('div');
            thumb.className = 'gallery-thumbnail';
            thumb.dataset.plotType = plotType;

            const img = document.createElement('img');
            img.src = `/static/vis_app/img/plot_gallery/${category}/${data.thumbnail}`;
            img.alt = data.name;

            const label = document.createElement('div');
            label.className = 'gallery-thumbnail-label';
            label.textContent = data.name;

            thumb.appendChild(img);
            thumb.appendChild(label);

            // Click handler to show plot info
            thumb.addEventListener('click', () => {
                this.showPlotInfo(plotType);
            });

            thumbnailsContainer.appendChild(thumb);
        });

        console.log(`[GalleryUI] Loaded ${plotTypes.length} thumbnails for category: ${category}`);
    }

    /**
     * Show detailed information about a selected plot type
     */
    private showPlotInfo(plotType: string): void {
        const data = this.galleryData.getPlotInfo(plotType);
        if (!data) return;

        // Update selected state
        this.gallerySelectedPlotType = plotType;
        document.querySelectorAll('.gallery-thumbnail').forEach(thumb => {
            if ((thumb as HTMLElement).dataset.plotType === plotType) {
                thumb.classList.add('selected');
            } else {
                thumb.classList.remove('selected');
            }
        });

        // Update info panel
        const nameEl = document.getElementById('gallery-plot-name');
        const descEl = document.getElementById('gallery-plot-desc');
        const requiredEl = document.getElementById('gallery-required-cols');
        const optionalEl = document.getElementById('gallery-optional-cols');
        const infoPanel = document.getElementById('gallery-info');

        if (nameEl) nameEl.textContent = data.name;
        if (descEl) descEl.textContent = data.description;
        if (requiredEl) requiredEl.textContent = data.data_columns.required.join(', ');
        if (optionalEl) optionalEl.textContent = data.data_columns.optional.join(', ') || 'None';
        if (infoPanel) infoPanel.style.display = 'block';

        console.log(`[GalleryUI] Showing info for plot type: ${plotType}`);
    }
}
