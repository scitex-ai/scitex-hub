/**
 * PanelControls - Manages sidebar and properties panel toggle functionality
 *
 * Responsibilities:
 * - Initialize sidebar toggle with state management
 * - Initialize properties panel toggle with state management
 * - Handle CSS class toggling for collapsed states
 * - Update toggle button icons based on state
 */

export class PanelControls {
    private isSidebarCollapsed: boolean = false;
    private isPropertiesCollapsed: boolean = false;

    constructor(
        private statusBarCallback?: (message: string) => void
    ) {}

    /**
     * Initialize sidebar toggle button and event listeners
     */
    public initSidebarToggle(): void {
        const toggleBtn = document.getElementById('sidebar-toggle');
        const main = document.querySelector('.vis-main');
        const icon = toggleBtn?.querySelector('i');

        toggleBtn?.addEventListener('click', () => {
            this.isSidebarCollapsed = !this.isSidebarCollapsed;
            main?.classList.toggle('sidebar-collapsed', this.isSidebarCollapsed);

            // Update icon
            if (icon) {
                icon.className = this.isSidebarCollapsed
                    ? 'fas fa-chevron-right'
                    : 'fas fa-chevron-left';
            }

            console.log(`[PanelControls] Sidebar collapsed: ${this.isSidebarCollapsed}`);
        });
    }

    /**
     * Initialize properties panel toggle button and event listeners
     */
    public initPropertiesToggle(): void {
        const toggleBtn = document.getElementById('properties-toggle');
        const main = document.querySelector('.vis-main');
        const icon = toggleBtn?.querySelector('i');

        toggleBtn?.addEventListener('click', () => {
            this.isPropertiesCollapsed = !this.isPropertiesCollapsed;
            main?.classList.toggle('properties-collapsed', this.isPropertiesCollapsed);

            // Update icon
            if (icon) {
                icon.className = this.isPropertiesCollapsed
                    ? 'fas fa-chevron-left'
                    : 'fas fa-chevron-right';
            }

            console.log(`[PanelControls] Properties panel collapsed: ${this.isPropertiesCollapsed}`);
        });
    }

    /**
     * Get sidebar collapse state
     */
    public isSidebarCollapsedState(): boolean {
        return this.isSidebarCollapsed;
    }

    /**
     * Get properties panel collapse state
     */
    public isPropertiesCollapsedState(): boolean {
        return this.isPropertiesCollapsed;
    }

    /**
     * Set sidebar collapse state programmatically
     */
    public setSidebarCollapsed(collapsed: boolean): void {
        this.isSidebarCollapsed = collapsed;
        const main = document.querySelector('.vis-main');
        const toggleBtn = document.getElementById('sidebar-toggle');
        const icon = toggleBtn?.querySelector('i');

        main?.classList.toggle('sidebar-collapsed', collapsed);
        if (icon) {
            icon.className = collapsed
                ? 'fas fa-chevron-right'
                : 'fas fa-chevron-left';
        }
    }

    /**
     * Set properties panel collapse state programmatically
     */
    public setPropertiesCollapsed(collapsed: boolean): void {
        this.isPropertiesCollapsed = collapsed;
        const main = document.querySelector('.vis-main');
        const toggleBtn = document.getElementById('properties-toggle');
        const icon = toggleBtn?.querySelector('i');

        main?.classList.toggle('properties-collapsed', collapsed);
        if (icon) {
            icon.className = collapsed
                ? 'fas fa-chevron-left'
                : 'fas fa-chevron-right';
        }
    }
}
