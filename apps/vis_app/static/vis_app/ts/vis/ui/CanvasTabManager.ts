/**
 * CanvasTabManager - Manages tabs for canvas/figures
 *
 * Responsibilities:
 * - Figure tab creation and management
 * - Tab switching between figures (saves/restores canvas state)
 * - Tab close functionality
 * - Inline rename on double-click
 * - 1 tab = 1 canvas (independent canvas state per tab)
 */

export interface CanvasTab {
    id: string;
    figureName: string;
    isActive: boolean;
    /** Serialized canvas JSON (fabric.js toJSON output) */
    canvasJson?: any;
    /** View state: zoom level and pan offset */
    viewState?: {
        zoom: number;
        panX: number;
        panY: number;
    };
}

export class CanvasTabManager {
    private tabs: CanvasTab[] = [];
    private activeTabId: string | null = null;
    private onBeforeTabChange: (() => void) | null = null;  // Called before switching to save current state
    private onTabChange: ((tabId: string) => void) | null = null;
    private onTabClose: ((tabId: string) => void) | null = null;
    private onTabRename: ((tabId: string, newName: string) => void) | null = null;

    constructor() {
        this.initializeDefaultTab();
    }

    /**
     * Initialize with a default tab (Figure 1)
     */
    private initializeDefaultTab(): void {
        const defaultTab: CanvasTab = {
            id: 'default',
            figureName: 'Figure 1',
            isActive: true
        };
        this.tabs.push(defaultTab);
        this.activeTabId = 'default';
    }

    /**
     * Set callbacks
     */
    public setCallbacks(
        onTabChange: (tabId: string) => void,
        onTabClose: (tabId: string) => void,
        onTabRename: (tabId: string, newName: string) => void,
        onBeforeTabChange?: () => void
    ): void {
        this.onTabChange = onTabChange;
        this.onTabClose = onTabClose;
        this.onTabRename = onTabRename;
        this.onBeforeTabChange = onBeforeTabChange || null;
    }

    /**
     * Create a new figure tab
     */
    public createTab(figureName?: string): string {
        const id = `canvas-tab-${Date.now()}`;

        // Auto-generate figure name if not provided
        const figName = figureName || `Figure ${this.tabs.length + 1}`;

        const newTab: CanvasTab = {
            id,
            figureName: figName,
            isActive: false
        };
        this.tabs.push(newTab);
        this.renderTabs();

        // Persist updated tabs to storage
        this.saveTabsToStorage();

        return id;
    }

    /**
     * Switch to a tab
     */
    public switchToTab(tabId: string): void {
        const tab = this.tabs.find(t => t.id === tabId);
        if (!tab) return;

        // Don't switch if already active
        if (this.activeTabId === tabId) return;

        // Save current canvas state BEFORE switching
        if (this.onBeforeTabChange) {
            this.onBeforeTabChange();
        }

        this.tabs.forEach(t => t.isActive = false);
        tab.isActive = true;
        this.activeTabId = tabId;
        this.renderTabs();

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

        // Persist updated tabs to storage
        this.saveTabsToStorage();

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

        tab.figureName = newName;
        this.renderTabs();

        // Persist updated tabs to storage
        this.saveTabsToStorage();

        if (this.onTabRename) {
            this.onTabRename(tabId, newName);
        }
    }

    /**
     * Render dropdown menu items
     */
    public renderTabs(): void {
        const menu = document.getElementById('figure-dropdown-menu');
        const label = document.getElementById('figure-dropdown-label');
        if (!menu) return;

        menu.innerHTML = '';

        this.tabs.forEach(tab => {
            const itemElement = this.createDropdownItem(tab);
            menu.appendChild(itemElement);
        });

        // Update the dropdown toggle label to show active tab
        const activeTab = this.getActiveTab();
        if (label && activeTab) {
            label.textContent = activeTab.figureName;
        }
    }

    /**
     * Create a dropdown item element
     */
    private createDropdownItem(tab: CanvasTab): HTMLElement {
        const item = document.createElement('div');
        item.className = `figure-dropdown-item${tab.isActive ? ' active' : ''}`;
        item.dataset.tabId = tab.id;

        // Icon
        const icon = document.createElement('i');
        icon.className = 'fas fa-paint-brush';
        item.appendChild(icon);

        // Label
        const label = document.createElement('span');
        label.className = 'figure-dropdown-item-label';
        label.textContent = tab.figureName;
        item.appendChild(label);

        // Close button (only show if more than 1 tab)
        if (this.tabs.length > 1) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'figure-dropdown-item-close';
            closeBtn.title = 'Close figure';
            closeBtn.innerHTML = '&times;';
            closeBtn.onclick = (e) => {
                e.stopPropagation();
                this.closeTab(tab.id);
            };
            item.appendChild(closeBtn);
        }

        // Click to switch
        item.onclick = (e) => {
            if ((e.target as HTMLElement).classList.contains('figure-dropdown-item-close')) return;
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
     * Start inline rename in dropdown
     */
    private startInlineRename(itemElement: HTMLElement, tabId: string, labelElement: HTMLElement): void {
        const currentName = labelElement.textContent || '';

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'figure-rename-input';
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
     * Toggle dropdown open/close
     */
    private toggleDropdown(): void {
        const container = document.getElementById('figure-dropdown-container');
        if (container) {
            container.classList.toggle('open');
        }
    }

    /**
     * Close dropdown
     */
    private closeDropdown(): void {
        const container = document.getElementById('figure-dropdown-container');
        if (container) {
            container.classList.remove('open');
        }
    }

    /**
     * Get active tab
     */
    public getActiveTab(): CanvasTab | null {
        return this.tabs.find(t => t.id === this.activeTabId) || null;
    }

    /**
     * Get all tabs
     */
    public getTabs(): CanvasTab[] {
        return [...this.tabs];
    }

    /**
     * Save canvas state to the active tab
     * Called before switching tabs to preserve current canvas content
     */
    public saveCanvasState(canvasJson: any, viewState?: { zoom: number; panX: number; panY: number }): void {
        const activeTab = this.tabs.find(t => t.id === this.activeTabId);
        if (activeTab) {
            activeTab.canvasJson = canvasJson;
            if (viewState) {
                activeTab.viewState = viewState;
            }
            console.log(`[CanvasTabManager] Saved state for tab: ${activeTab.figureName}`);
            // Persist to localStorage
            this.saveTabsToStorage();
        }
    }

    /**
     * Get canvas state for a specific tab
     */
    public getTabState(tabId: string): { canvasJson?: any; viewState?: { zoom: number; panX: number; panY: number } } | null {
        const tab = this.tabs.find(t => t.id === tabId);
        if (!tab) return null;
        return {
            canvasJson: tab.canvasJson,
            viewState: tab.viewState
        };
    }

    /**
     * Save all tabs to localStorage for persistence across page reloads
     */
    private saveTabsToStorage(): void {
        try {
            const tabsData = this.tabs.map(tab => ({
                id: tab.id,
                figureName: tab.figureName,
                isActive: tab.isActive,
                canvasJson: tab.canvasJson,
                viewState: tab.viewState
            }));
            localStorage.setItem('scitex-vis-canvas-tabs', JSON.stringify(tabsData));
        } catch (err) {
            console.warn('[CanvasTabManager] Failed to save tabs to storage:', err);
        }
    }

    /**
     * Load tabs from localStorage
     */
    public loadTabsFromStorage(): boolean {
        try {
            const saved = localStorage.getItem('scitex-vis-canvas-tabs');
            if (saved) {
                const tabsData = JSON.parse(saved);
                if (Array.isArray(tabsData) && tabsData.length > 0) {
                    this.tabs = tabsData;
                    this.activeTabId = tabsData.find((t: CanvasTab) => t.isActive)?.id || tabsData[0].id;
                    console.log(`[CanvasTabManager] Loaded ${this.tabs.length} tabs from storage`);
                    return true;
                }
            }
        } catch (err) {
            console.warn('[CanvasTabManager] Failed to load tabs from storage:', err);
        }
        return false;
    }

    /**
     * Initialize event listeners for dropdown and new tab button
     */
    public initializeEventListeners(): void {
        // Dropdown toggle
        const toggleBtn = document.getElementById('figure-dropdown-toggle');
        if (toggleBtn) {
            toggleBtn.onclick = (e) => {
                e.stopPropagation();
                this.toggleDropdown();
            };
        }

        // New figure button
        const newTabBtn = document.getElementById('canvas-tab-new');
        if (newTabBtn) {
            newTabBtn.onclick = () => {
                this.showInlineNewTabInput();
            };
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const container = document.getElementById('figure-dropdown-container');
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
        const menu = document.getElementById('figure-dropdown-menu');
        if (!menu) return;

        // Open dropdown first
        const container = document.getElementById('figure-dropdown-container');
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
        inputItem.className = 'figure-dropdown-item inline-new-tab-wrapper';

        // Icon
        const icon = document.createElement('i');
        icon.className = 'fas fa-paint-brush';
        inputItem.appendChild(icon);

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'inline-new-tab-input figure-rename-input';
        const defaultFigureName = `Figure ${this.tabs.length + 1}`;
        input.value = defaultFigureName;
        input.placeholder = defaultFigureName;

        inputItem.appendChild(input);
        menu.appendChild(inputItem);

        input.focus();
        input.select();

        // Flag to prevent double execution from both Enter key and blur event
        let isFinished = false;

        const finishCreate = () => {
            if (isFinished) return;
            isFinished = true;
            const figureName = input.value.trim() || defaultFigureName;
            inputItem.remove();
            const newTabId = this.createTab(figureName);
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

    /**
     * Setup drag and drop handlers for tab reordering
     */
    private setupDragHandlers(tabElement: HTMLElement, tabId: string): void {
        tabElement.addEventListener('dragstart', (e: DragEvent) => {
            if (e.dataTransfer) {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', tabId);
            }
            tabElement.classList.add('dragging');
        });

        tabElement.addEventListener('dragend', () => {
            tabElement.classList.remove('dragging');
            // Remove all drag-over indicators
            document.querySelectorAll('.data-tab').forEach(el => {
                el.classList.remove('drag-over');
            });
        });

        tabElement.addEventListener('dragover', (e: DragEvent) => {
            e.preventDefault();
            if (e.dataTransfer) {
                e.dataTransfer.dropEffect = 'move';
            }
            tabElement.classList.add('drag-over');
        });

        tabElement.addEventListener('dragleave', () => {
            tabElement.classList.remove('drag-over');
        });

        tabElement.addEventListener('drop', (e: DragEvent) => {
            e.preventDefault();
            tabElement.classList.remove('drag-over');

            if (e.dataTransfer) {
                const draggedId = e.dataTransfer.getData('text/plain');
                this.reorderTabs(draggedId, tabId);
            }
        });
    }

    /**
     * Reorder tabs by moving draggedId before targetId
     */
    private reorderTabs(draggedId: string, targetId: string): void {
        if (draggedId === targetId) return;

        const draggedIndex = this.tabs.findIndex(t => t.id === draggedId);
        const targetIndex = this.tabs.findIndex(t => t.id === targetId);

        if (draggedIndex === -1 || targetIndex === -1) return;

        // Remove dragged tab and insert before target
        const [draggedTab] = this.tabs.splice(draggedIndex, 1);
        this.tabs.splice(targetIndex, 0, draggedTab);

        this.renderTabs();
    }
}
