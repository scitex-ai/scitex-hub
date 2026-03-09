/**
 * ToolbarManager - Manages toolbar state and tool activation
 *
 * Responsibilities:
 * - Ensure toolbar sections are collapsed on init
 * - Toggle toolbar panel visibility
 * - Activate tools via callback
 * - Handle collapsible section interactions
 */

export class ToolbarManager {
    constructor(
        private onToolActivate?: (tool: string) => void,
        private onToggle?: () => void
    ) {}

    /**
     * Setup toolbar on initialization
     */
    public setupToolbar(): void {
        this.ensureToolbarCollapsed();
        this.setupCollapsibleSections();
        this.setupToolButtons();
        this.setupToggleButton();
        console.log('[ToolbarManager] Toolbar initialized');
    }

    /**
     * Ensure all toolbar sections start collapsed
     */
    public ensureToolbarCollapsed(): void {
        const sections = document.querySelectorAll('.toolbar-section');
        sections.forEach(section => {
            if (!section.classList.contains('collapsed')) {
                section.classList.add('collapsed');
            }
        });
        console.log('[ToolbarManager] All toolbar sections collapsed');
    }

    /**
     * Toggle toolbar panel visibility
     */
    public toggleToolbarPanel(): void {
        const toolbar = document.querySelector('.vis-toolbar');
        const toggleBtn = document.getElementById('toggle-toolbar');

        if (toolbar && toggleBtn) {
            toolbar.classList.toggle('minimized');
            const isMinimized = toolbar.classList.contains('minimized');

            // Update button icon
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.className = isMinimized ? 'fas fa-chevron-right' : 'fas fa-chevron-left';
            }

            // Notify parent
            if (this.onToggle) {
                this.onToggle();
            }
        }
    }

    /**
     * Setup collapsible toolbar sections
     */
    private setupCollapsibleSections(): void {
        document.querySelectorAll('.collapsible-header').forEach(header => {
            header.addEventListener('click', (e) => {
                const section = (e.currentTarget as HTMLElement).closest('.toolbar-section');
                if (section) {
                    section.classList.toggle('collapsed');
                }
            });
        });
    }

    /**
     * Setup tool button click handlers
     */
    private setupToolButtons(): void {
        document.querySelectorAll('[data-tool]').forEach(button => {
            button.addEventListener('click', (e) => {
                const tool = (e.currentTarget as HTMLElement).dataset.tool;
                if (tool && this.onToolActivate) {
                    this.onToolActivate(tool);
                }
            });
        });
    }

    /**
     * Setup toolbar toggle button
     */
    private setupToggleButton(): void {
        const toggleToolbar = document.getElementById('toggle-toolbar');
        if (toggleToolbar) {
            toggleToolbar.addEventListener('click', () => this.toggleToolbarPanel());
        }
    }
}
