/**
 * ZenPanelManager - Panel state management for zen mode
 *
 * Responsibilities:
 * - Capture current panel collapse states
 * - Collapse all panels for zen mode
 * - Expand all panels (for default state)
 * - Restore saved panel states
 * - Update toggle button icons
 *
 * Extracted from zen-mode.ts for single responsibility.
 */

export interface PanelConfig {
    headerSelector: string;
    sidebarSelector?: string;
    detailsSelector?: string;
    sidebarToggleId?: string;
    detailsToggleId?: string;
    storagePrefix?: string;
}

export interface SavedPanelStates {
    headerCollapsed: boolean;
    sidebarCollapsed: boolean;
    detailsCollapsed: boolean;
}

export class ZenPanelManager {
    constructor(private config: PanelConfig) {}

    /**
     * Capture current panel collapse states
     */
    public captureCurrentStates(): SavedPanelStates {
        const header = document.querySelector(this.config.headerSelector) as HTMLElement;
        const sidebar = this.config.sidebarSelector
            ? document.querySelector(this.config.sidebarSelector) as HTMLElement
            : null;
        const details = this.config.detailsSelector
            ? document.querySelector(this.config.detailsSelector) as HTMLElement
            : null;

        return {
            headerCollapsed: header?.classList.contains('collapsed') ?? false,
            sidebarCollapsed: sidebar?.classList.contains('collapsed') ?? false,
            detailsCollapsed: details?.classList.contains('collapsed') ?? false,
        };
    }

    /**
     * Collapse all panels for zen mode
     */
    public collapseAllPanels(): void {
        // Collapse header
        const header = document.querySelector(this.config.headerSelector) as HTMLElement;
        if (header && !header.classList.contains('collapsed')) {
            header.classList.add('collapsed');
        }

        // Collapse sidebar
        if (this.config.sidebarSelector) {
            const sidebar = document.querySelector(this.config.sidebarSelector) as HTMLElement;
            if (sidebar && !sidebar.classList.contains('collapsed')) {
                sidebar.classList.add('collapsed');
                sidebar.style.width = '';
                sidebar.style.flexShrink = '';
                sidebar.style.flexGrow = '';

                if (this.config.sidebarToggleId) {
                    const toggleBtn = document.getElementById(this.config.sidebarToggleId);
                    if (toggleBtn) {
                        this.updateToggleIcon(toggleBtn, 'left', true);
                    }
                }
            }
        }

        // Collapse details panel
        if (this.config.detailsSelector) {
            const details = document.querySelector(this.config.detailsSelector) as HTMLElement;
            if (details && !details.classList.contains('collapsed')) {
                details.classList.add('collapsed');
                details.style.width = '';
                details.style.flexShrink = '';
                details.style.flexGrow = '';

                if (this.config.detailsToggleId) {
                    const toggleBtn = document.getElementById(this.config.detailsToggleId);
                    if (toggleBtn) {
                        this.updateToggleIcon(toggleBtn, 'right', true);
                    }
                }
            }
        }
    }

    /**
     * Expand all panels (for #default hash)
     */
    public expandAllPanels(): void {
        const storagePrefix = this.config.storagePrefix || 'scitex-';

        // Expand header
        const header = document.querySelector(this.config.headerSelector) as HTMLElement;
        if (header) {
            header.classList.remove('collapsed');
            localStorage.setItem('scitex-header-collapsed', 'false');
        }

        // Expand sidebar
        if (this.config.sidebarSelector) {
            const sidebar = document.querySelector(this.config.sidebarSelector) as HTMLElement;
            if (sidebar) {
                sidebar.classList.remove('collapsed');
                const savedWidth = localStorage.getItem(`${storagePrefix}sidebar-width`);
                if (savedWidth) {
                    const width = parseInt(savedWidth, 10);
                    if (width > 40) {
                        sidebar.style.width = `${width}px`;
                        sidebar.style.flexShrink = '0';
                        sidebar.style.flexGrow = '0';
                    }
                }

                if (this.config.sidebarToggleId) {
                    const toggleBtn = document.getElementById(this.config.sidebarToggleId);
                    if (toggleBtn) {
                        this.updateToggleIcon(toggleBtn, 'left', false);
                    }
                }

                localStorage.setItem(`${storagePrefix}sidebar-collapsed`, 'false');
            }
        }

        // Expand details panel
        if (this.config.detailsSelector) {
            const details = document.querySelector(this.config.detailsSelector) as HTMLElement;
            if (details) {
                details.classList.remove('collapsed');
                const savedWidth = localStorage.getItem(`${storagePrefix}details-width`);
                if (savedWidth) {
                    const width = parseInt(savedWidth, 10);
                    if (width > 40) {
                        details.style.width = `${width}px`;
                        details.style.flexShrink = '0';
                        details.style.flexGrow = '0';
                    }
                }

                if (this.config.detailsToggleId) {
                    const toggleBtn = document.getElementById(this.config.detailsToggleId);
                    if (toggleBtn) {
                        this.updateToggleIcon(toggleBtn, 'right', false);
                    }
                }

                localStorage.setItem(`${storagePrefix}details-collapsed`, 'false');
            }
        }
    }

    /**
     * Restore panel states from saved states
     */
    public restorePanelStates(states: SavedPanelStates): void {
        const storagePrefix = this.config.storagePrefix || 'scitex-';

        // Restore header
        const header = document.querySelector(this.config.headerSelector) as HTMLElement;
        if (header) {
            if (states.headerCollapsed) {
                header.classList.add('collapsed');
            } else {
                header.classList.remove('collapsed');
            }
            localStorage.setItem('scitex-header-collapsed', states.headerCollapsed.toString());
        }

        // Restore sidebar
        if (this.config.sidebarSelector) {
            const sidebar = document.querySelector(this.config.sidebarSelector) as HTMLElement;
            if (sidebar) {
                if (states.sidebarCollapsed) {
                    sidebar.classList.add('collapsed');
                    sidebar.style.width = '';
                } else {
                    sidebar.classList.remove('collapsed');
                    const savedWidth = localStorage.getItem(`${storagePrefix}sidebar-width`);
                    if (savedWidth) {
                        const width = parseInt(savedWidth, 10);
                        if (width > 40) {
                            sidebar.style.width = `${width}px`;
                            sidebar.style.flexShrink = '0';
                            sidebar.style.flexGrow = '0';
                        }
                    }
                }

                if (this.config.sidebarToggleId) {
                    const toggleBtn = document.getElementById(this.config.sidebarToggleId);
                    if (toggleBtn) {
                        this.updateToggleIcon(toggleBtn, 'left', states.sidebarCollapsed);
                    }
                }

                localStorage.setItem(`${storagePrefix}sidebar-collapsed`, states.sidebarCollapsed.toString());
            }
        }

        // Restore details panel
        if (this.config.detailsSelector) {
            const details = document.querySelector(this.config.detailsSelector) as HTMLElement;
            if (details) {
                if (states.detailsCollapsed) {
                    details.classList.add('collapsed');
                    details.style.width = '';
                } else {
                    details.classList.remove('collapsed');
                    const savedWidth = localStorage.getItem(`${storagePrefix}details-width`);
                    if (savedWidth) {
                        const width = parseInt(savedWidth, 10);
                        if (width > 40) {
                            details.style.width = `${width}px`;
                            details.style.flexShrink = '0';
                            details.style.flexGrow = '0';
                        }
                    }
                }

                if (this.config.detailsToggleId) {
                    const toggleBtn = document.getElementById(this.config.detailsToggleId);
                    if (toggleBtn) {
                        this.updateToggleIcon(toggleBtn, 'right', states.detailsCollapsed);
                    }
                }

                localStorage.setItem(`${storagePrefix}details-collapsed`, states.detailsCollapsed.toString());
            }
        }
    }

    /**
     * Update toggle button icon
     */
    private updateToggleIcon(toggleBtn: HTMLElement, direction: 'left' | 'right', isCollapsed: boolean): void {
        const icon = toggleBtn.querySelector('i');
        if (!icon) return;

        if (direction === 'left') {
            if (isCollapsed) {
                icon.classList.remove('fa-chevron-left');
                icon.classList.add('fa-chevron-right');
            } else {
                icon.classList.remove('fa-chevron-right');
                icon.classList.add('fa-chevron-left');
            }
        } else {
            if (isCollapsed) {
                icon.classList.remove('fa-chevron-right');
                icon.classList.add('fa-chevron-left');
            } else {
                icon.classList.remove('fa-chevron-left');
                icon.classList.add('fa-chevron-right');
            }
        }
    }
}
