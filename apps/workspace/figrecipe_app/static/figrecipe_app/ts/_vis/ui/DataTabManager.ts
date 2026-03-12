/**
 * DataTabManager - Manages tabs for data tables (line objects)
 *
 * Responsibilities:
 * - Tab creation and management
 * - Tab switching
 * - Tab close functionality
 * - Inline rename on double-click
 *
 * Refactored: DataTabInlineInput handles inline input logic.
 */

import { startInlineRename, showInlineNewTabInput } from './DataTabInlineInput';

export interface DataTab {
    id: string;
    name: string;
    /** ID of the linked figure (canvas tab) - bidirectional link */
    linkedFigureId?: string;
    figureName?: string;  // Figure name for tab display (deprecated, use linkedFigureId)
    objectName?: string;  // Object name for tab display (line, scatter, etc.)
    type: 'line' | 'scatter' | 'categorical' | 'distribution' | 'statistical' | 'grid' | 'area' | 'contour' | 'vector' | 'special' | 'default';
    isActive: boolean;
    data?: any;
}

export class DataTabManager {
    private tabs: DataTab[] = [];
    private activeTabId: string | null = null;
    private onTabChange: ((tabId: string) => void) | null = null;
    private onTabClose: ((tabId: string) => void) | null = null;
    private onTabRename: ((tabId: string, newName: string) => void) | null = null;

    constructor() {
        // No default tabs - tabs are created when figures/data are loaded
    }

    /**
     * Sanitize name for filesystem compatibility
     */
    private sanitizeName(name: string): string {
        return name.replace(/\s+/g, '').replace(/[<>:"/\\|?*]/g, '');
    }

    /**
     * Set callbacks
     */
    public setCallbacks(
        onTabChange: (tabId: string) => void,
        onTabClose: (tabId: string) => void,
        onTabRename: (tabId: string, newName: string) => void
    ): void {
        this.onTabChange = onTabChange;
        this.onTabClose = onTabClose;
        this.onTabRename = onTabRename;
    }

    /**
     * Create a new tab
     * Names are sanitized (no spaces) for filesystem compatibility
     */
    public createTab(
        name: string,
        type: DataTab['type'] = 'default',
        figureName?: string,
        objectName?: string,
        data?: any
    ): string {
        const id = `tab-${Date.now()}`;

        // Sanitize name for filesystem compatibility
        const sanitizedName = this.sanitizeName(name);
        const sanitizedObjectName = objectName ? this.sanitizeName(objectName) : sanitizedName;
        const sanitizedFigureName = figureName ? this.sanitizeName(figureName) : undefined;

        const newTab: DataTab = {
            id,
            name: sanitizedName,
            figureName: sanitizedFigureName,
            objectName: sanitizedObjectName,
            type,
            isActive: false,
            data
        };
        this.tabs.push(newTab);
        this.renderTabs();
        return id;
    }

    /**
     * Create a new tab and switch to it
     */
    public createAndSwitchToTab(
        name: string,
        type: DataTab['type'] = 'line',
        figureName?: string,
        objectName?: string,
        data?: any
    ): string {
        const tabId = this.createTab(name, type, figureName, objectName, data);
        this.switchToTab(tabId);
        return tabId;
    }

    /**
     * Get tab data by ID
     */
    public getTabData(tabId: string): any {
        const tab = this.tabs.find(t => t.id === tabId);
        return tab?.data;
    }

    /**
     * Update tab data
     */
    public updateTabData(tabId: string, data: any): void {
        const tab = this.tabs.find(t => t.id === tabId);
        if (tab) {
            tab.data = data;
        }
    }

    /**
     * Switch to a tab
     */
    public switchToTab(tabId: string): void {
        const tab = this.tabs.find(t => t.id === tabId);
        if (!tab) return;

        this.tabs.forEach(t => t.isActive = false);
        tab.isActive = true;
        this.activeTabId = tabId;
        this.renderTabs();

        // Scroll to make the active tab visible
        requestAnimationFrame(() => {
            this.scrollToActiveTab();
        });

        if (this.onTabChange) {
            this.onTabChange(tabId);
        }
    }

    /**
     * Close a tab
     */
    public closeTab(tabId: string): void {
        const index = this.tabs.findIndex(t => t.id === tabId);
        if (index === -1) return;

        this.tabs.splice(index, 1);

        // If closing active tab, switch to another or set null
        if (this.activeTabId === tabId) {
            if (this.tabs.length > 0) {
                const newActiveIndex = Math.min(index, this.tabs.length - 1);
                this.switchToTab(this.tabs[newActiveIndex].id);
            } else {
                this.activeTabId = null;
                this.renderTabs();
            }
        } else {
            this.renderTabs();
        }

        if (this.onTabClose) {
            this.onTabClose(tabId);
        }
    }

    /**
     * Rename a tab
     */
    public renameTab(tabId: string, newName: string): void {
        const tab = this.tabs.find(t => t.id === tabId);
        if (!tab) return;

        tab.name = newName;
        this.renderTabs();

        if (this.onTabRename) {
            this.onTabRename(tabId, newName);
        }
    }

    /**
     * Render dropdown menu items
     */
    public renderTabs(): void {
        const menu = document.getElementById('data-dropdown-menu');
        const label = document.getElementById('data-dropdown-label');
        if (!menu) return;

        menu.innerHTML = '';

        if (this.tabs.length === 0) {
            // Empty state - show prompt
            const emptyState = document.createElement('div');
            emptyState.className = 'data-dropdown-empty';
            emptyState.innerHTML = `
                <i class="fas fa-table"></i>
                <span>No tables yet</span>
                <small>Click + to create</small>
            `;
            menu.appendChild(emptyState);
            if (label) label.textContent = 'No tables';

            // Reset toggle icon to default
            const toggleIcon = document.querySelector('#data-dropdown-toggle i:first-child');
            if (toggleIcon) {
                toggleIcon.className = 'fas fa-table';
            }
        } else {
            this.tabs.forEach(tab => {
                const itemElement = this.createDropdownItem(tab);
                menu.appendChild(itemElement);
            });

            // Update the dropdown toggle label to show active tab
            const activeTab = this.getActiveTab();
            if (label && activeTab) {
                label.textContent = activeTab.name;
            }

            // Update toggle icon based on active tab type
            const toggleIcon = document.querySelector('#data-dropdown-toggle i:first-child');
            if (toggleIcon && activeTab) {
                toggleIcon.className = this.getIconClass(activeTab.type);
            }
        }
    }

    /**
     * Create a dropdown item element
     */
    private createDropdownItem(tab: DataTab): HTMLElement {
        const item = document.createElement('div');
        item.className = `data-dropdown-item${tab.isActive ? ' active' : ''}`;
        item.dataset.tabId = tab.id;

        // Icon based on type
        const icon = document.createElement('i');
        icon.className = this.getIconClass(tab.type);
        item.appendChild(icon);

        // Label
        const label = document.createElement('span');
        label.className = 'data-dropdown-item-label';
        label.textContent = tab.name;
        item.appendChild(label);

        // Close button (only show if more than 1 tab)
        if (this.tabs.length > 1) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'data-dropdown-item-close';
            closeBtn.title = 'Close data table';
            closeBtn.innerHTML = '&times;';
            closeBtn.onclick = (e) => {
                e.stopPropagation();
                this.closeTab(tab.id);
            };
            item.appendChild(closeBtn);
        }

        // Click to switch
        item.onclick = (e) => {
            if ((e.target as HTMLElement).classList.contains('data-dropdown-item-close')) return;
            this.switchToTab(tab.id);
            this.closeDropdown();
        };

        // Double-click to rename
        item.ondblclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            startInlineRename(
                item,
                label,
                tab.name,
                this.sanitizeName.bind(this),
                (newName) => this.renameTab(tab.id, newName)
            );
        };

        return item;
    }

    /**
     * Toggle dropdown open/close
     */
    private toggleDropdown(): void {
        const container = document.getElementById('data-dropdown-container');
        if (container) {
            container.classList.toggle('open');
        }
    }

    /**
     * Close dropdown
     */
    private closeDropdown(): void {
        const container = document.getElementById('data-dropdown-container');
        if (container) {
            container.classList.remove('open');
        }
    }

    /**
     * Get icon class based on tab type
     * Icons match the gallery category buttons in canvas pane
     */
    private getIconClass(type: DataTab['type']): string {
        switch (type) {
            case 'line':
                return 'fas fa-chart-line';
            case 'scatter':
                return 'fas fa-braille';
            case 'categorical':
                return 'fas fa-chart-bar';
            case 'distribution':
                return 'fas fa-chart-column';
            case 'statistical':
                return 'fas fa-square-root-variable';
            case 'grid':
                return 'fas fa-th';
            case 'area':
                return 'fas fa-chart-area';
            case 'contour':
                return 'fas fa-layer-group';
            case 'vector':
                return 'fas fa-arrows-alt';
            case 'special':
                return 'fas fa-shapes';
            default:
                return 'fas fa-table';
        }
    }

    /**
     * Scroll dropdown menu to make the active tab visible
     */
    private scrollToActiveTab(): void {
        const menu = document.getElementById('data-dropdown-menu');
        const activeItem = menu?.querySelector('.data-dropdown-item.active') as HTMLElement;
        if (menu && activeItem) {
            activeItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    }

    /**
     * Get active tab
     */
    public getActiveTab(): DataTab | null {
        return this.tabs.find(t => t.id === this.activeTabId) || null;
    }

    /**
     * Get all tabs
     */
    public getTabs(): DataTab[] {
        return [...this.tabs];
    }

    /**
     * Get tabs linked to a specific figure
     */
    public getTabsForFigure(figureId: string): DataTab[] {
        return this.tabs.filter(t => t.linkedFigureId === figureId);
    }

    /**
     * Link a data table to a figure
     */
    public linkToFigure(tabId: string, figureId: string): void {
        const tab = this.tabs.find(t => t.id === tabId);
        if (tab) {
            tab.linkedFigureId = figureId;
        }
    }

    /**
     * Unlink a data table from its figure
     */
    public unlinkFromFigure(tabId: string): void {
        const tab = this.tabs.find(t => t.id === tabId);
        if (tab) {
            tab.linkedFigureId = undefined;
        }
    }

    /**
     * Validate tabs - remove tabs linked to figures that no longer exist.
     *
     * @param validFigureIds Array of valid figure tab IDs
     * @returns Number of tabs removed
     */
    public validateAndCleanTabs(validFigureIds: string[]): number {
        const initialCount = this.tabs.length;
        const validIdSet = new Set(validFigureIds);

        this.tabs = this.tabs.filter(tab => {
            // Keep tabs without linkedFigureId (standalone tables)
            if (!tab.linkedFigureId) return true;

            // Keep if linked figure still exists
            const exists = validIdSet.has(tab.linkedFigureId);
            if (!exists) {
                console.log(`[DataTabManager] Removing stale tab: ${tab.name} (linked to ${tab.linkedFigureId})`);
            }
            return exists;
        });

        const removedCount = initialCount - this.tabs.length;

        // No default tab - empty state is valid (filesystem is source of truth)

        // Update active tab if it was removed
        if (this.activeTabId && !this.tabs.find(t => t.id === this.activeTabId)) {
            this.activeTabId = this.tabs[0]?.id || null;
            this.tabs.forEach(t => t.isActive = t.id === this.activeTabId);
        }

        if (removedCount > 0) {
            this.renderTabs();
            console.log(`[DataTabManager] Removed ${removedCount} stale tab(s)`);
        }

        return removedCount;
    }

    /**
     * Clear all tabs
     */
    public clearAllTabs(): void {
        this.tabs = [];
        this.activeTabId = null;
        this.renderTabs();
        console.log('[DataTabManager] Cleared all tabs');
    }

    /**
     * Initialize event listeners for dropdown and new tab button
     */
    public initializeEventListeners(): void {
        // Dropdown toggle
        const toggleBtn = document.getElementById('data-dropdown-toggle');
        if (toggleBtn) {
            toggleBtn.onclick = (e) => {
                e.stopPropagation();
                this.toggleDropdown();
            };
        }

        // New data table button
        const newTabBtn = document.getElementById('data-tab-new');
        if (newTabBtn) {
            newTabBtn.onclick = () => {
                this.doShowInlineNewTabInput();
            };
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const container = document.getElementById('data-dropdown-container');
            if (container && !container.contains(e.target as Node)) {
                this.closeDropdown();
            }
        });

        // Close dropdown on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeDropdown();
            }
        });
    }

    /**
     * Show inline input for creating a new tab (in dropdown menu)
     */
    private doShowInlineNewTabInput(): void {
        const menu = document.getElementById('data-dropdown-menu');
        if (!menu) return;

        // Open dropdown first
        const container = document.getElementById('data-dropdown-container');
        if (container) {
            container.classList.add('open');
        }

        const defaultTableName = `Table${this.tabs.length + 1}`;

        showInlineNewTabInput(
            menu,
            defaultTableName,
            this.sanitizeName.bind(this),
            (tableName) => {
                const newTabId = this.createTab(tableName, 'default', undefined, tableName);
                this.switchToTab(newTabId);
                this.closeDropdown();
            },
            () => {} // onCancel - no action needed
        );
    }

}
