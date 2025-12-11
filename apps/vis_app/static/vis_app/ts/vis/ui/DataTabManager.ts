/**
 * DataTabManager - Manages tabs for data tables (line objects)
 *
 * Responsibilities:
 * - Tab creation and management
 * - Tab switching
 * - Tab close functionality
 * - Inline rename on double-click
 */

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
        this.initializeDefaultTab();
    }

    /**
     * Initialize with a default tab
     */
    private initializeDefaultTab(): void {
        const defaultTab: DataTab = {
            id: 'default-data',
            name: 'Table 1',
            linkedFigureId: 'default',  // Links to default canvas figure
            objectName: 'Table 1',
            type: 'default',
            isActive: true
        };
        this.tabs.push(defaultTab);
        this.activeTabId = 'default-data';
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
     */
    public createTab(
        name: string,
        type: DataTab['type'] = 'default',
        figureName?: string,
        objectName?: string,
        data?: any
    ): string {
        const id = `tab-${Date.now()}`;

        // Use provided name directly as the tab name
        const newTab: DataTab = {
            id,
            name: name,
            figureName: figureName,
            objectName: objectName || name,
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

        // Don't close if it's the only tab
        if (this.tabs.length === 1) return;

        this.tabs.splice(index, 1);

        // If closing active tab, switch to another
        if (this.activeTabId === tabId) {
            const newActiveIndex = Math.min(index, this.tabs.length - 1);
            this.switchToTab(this.tabs[newActiveIndex].id);
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
            this.startInlineRename(item, tab.id, label);
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
     * Start inline rename in dropdown
     */
    private startInlineRename(itemElement: HTMLElement, tabId: string, labelElement: HTMLElement): void {
        const currentName = labelElement.textContent || '';

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'data-rename-input';
        input.value = currentName;

        labelElement.style.display = 'none';
        itemElement.insertBefore(input, labelElement.nextSibling);
        input.focus();
        input.select();

        let isFinished = false;
        const finishRename = () => {
            if (isFinished) return;
            isFinished = true;
            const newName = input.value.trim() || currentName;
            this.renameTab(tabId, newName);
            input.remove();
            labelElement.style.display = '';
        };

        input.onblur = finishRename;
        input.onkeydown = (e) => {
            e.stopPropagation();
            if (e.key === 'Enter') {
                e.preventDefault();
                finishRename();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                input.value = currentName;
                finishRename();
            }
        };
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
                this.showInlineNewTabInput();
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
    private showInlineNewTabInput(): void {
        const menu = document.getElementById('data-dropdown-menu');
        if (!menu) return;

        // Open dropdown first
        const container = document.getElementById('data-dropdown-container');
        if (container) {
            container.classList.add('open');
        }

        // Check if input already exists
        const existingInput = menu.querySelector('.inline-new-tab-input');
        if (existingInput) {
            (existingInput as HTMLInputElement).focus();
            return;
        }

        // Create inline input item
        const inputItem = document.createElement('div');
        inputItem.className = 'data-dropdown-item inline-new-tab-wrapper';

        // Icon (table icon for new tables)
        const icon = document.createElement('i');
        icon.className = 'fas fa-table';
        inputItem.appendChild(icon);

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'inline-new-tab-input data-rename-input';
        const defaultTableName = `Table ${this.tabs.length + 1}`;
        input.value = defaultTableName;
        input.placeholder = defaultTableName;

        inputItem.appendChild(input);
        menu.appendChild(inputItem);

        input.focus();
        input.select();

        // Flag to prevent double execution
        let isFinished = false;

        const finishCreate = () => {
            if (isFinished) return;
            isFinished = true;
            const tableName = input.value.trim() || defaultTableName;
            inputItem.remove();
            // Create table with default type
            const newTabId = this.createTab(tableName, 'default', undefined, tableName);
            this.switchToTab(newTabId);
            this.closeDropdown();
        };

        const cancelCreate = () => {
            if (isFinished) return;
            isFinished = true;
            inputItem.remove();
        };

        input.onblur = () => {
            setTimeout(() => {
                if (document.activeElement !== input) {
                    finishCreate();
                }
            }, 100);
        };

        input.onkeydown = (e) => {
            e.stopPropagation();
            if (e.key === 'Enter') {
                e.preventDefault();
                finishCreate();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelCreate();
            }
        };
    }

}
