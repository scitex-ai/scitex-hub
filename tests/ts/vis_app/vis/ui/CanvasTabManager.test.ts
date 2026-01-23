/**
 * Tests for apps/vis_app/static/vis_app/ts/vis/ui/CanvasTabManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/vis_app/static/vis_app/ts/vis/ui/CanvasTabManager';

describe('CanvasTabManager', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: apps/vis_app/static/vis_app/ts/vis/ui/CanvasTabManager.ts
// =============================================================================

// /**
//  * CanvasTabManager - Manages tabs for canvas/figures
//  *
//  * Responsibilities:
//  * - Figure tab creation and management
//  * - Tab switching between figures (saves/restores canvas state)
//  * - Tab close functionality
//  * - Inline rename on double-click
//  * - 1 tab = 1 canvas (independent canvas state per tab)
//  */
// 
// export interface CanvasTab {
//     id: string;
//     figureName: string;
//     isActive: boolean;
//     /** File path of the figz bundle (for tree sync) */
//     figurePath?: string;
//     /** IDs of linked data tables - bidirectional link with DataTab.linkedFigureId */
//     linkedDataTableIds?: string[];
//     /** Serialized canvas JSON (fabric.js toJSON output) */
//     canvasJson?: any;
//     /** View state: zoom level and pan offset */
//     viewState?: {
//         zoom: number;
//         panX: number;
//         panY: number;
//     };
// }
// 
// export class CanvasTabManager {
//     private tabs: CanvasTab[] = [];
//     private activeTabId: string | null = null;
//     private onBeforeTabChange: (() => void) | null = null;  // Called before switching to save current state
//     private onTabChange: ((tabId: string) => void) | null = null;
//     private onTabClose: ((tabId: string) => void) | null = null;
//     private onTabRename: ((tabId: string, newName: string) => void) | null = null;
//     private onBundleCreated: ((figureName: string, figurePath: string) => void) | null = null;
// 
//     constructor() {
//         this.initializeDefaultTab();
//     }
// 
//     /**
//      * Initialize with a default tab (Figure1)
//      */
//     private initializeDefaultTab(): void {
//         const defaultTab: CanvasTab = {
//             id: 'default',
//             figureName: 'Figure1',  // No space for filesystem compatibility
//             isActive: true,
//             linkedDataTableIds: ['default-data']  // Links to default data table
//         };
//         this.tabs.push(defaultTab);
//         this.activeTabId = 'default';
//     }
// 
//     /**
//      * Set callbacks
//      */
//     public setCallbacks(
//         onTabChange: (tabId: string) => void,
//         onTabClose: (tabId: string) => void,
//         onTabRename: (tabId: string, newName: string) => void,
//         onBeforeTabChange?: () => void,
//         onBundleCreated?: (figureName: string, figurePath: string) => void
//     ): void {
//         this.onTabChange = onTabChange;
//         this.onTabClose = onTabClose;
//         this.onTabRename = onTabRename;
//         this.onBeforeTabChange = onBeforeTabChange || null;
//         this.onBundleCreated = onBundleCreated || null;
//     }
// 
//     /**
//      * Create a figz bundle on the backend using scitex package
//      * Called when a new figure tab is created to ensure the bundle exists on disk
//      */
//     private async createFigzBundleOnBackend(figureName: string): Promise<string | null> {
//         const projectOwner = (window as any).projectOwner;
//         const projectSlug = (window as any).projectSlug;
// 
//         if (!projectOwner || !projectSlug) {
//             console.warn('[CanvasTabManager] No project context - cannot create figz bundle');
//             return null;
//         }
// 
//         try {
//             const csrfToken = this.getCSRFToken();
//             const response = await fetch('/vis/api/bundles/figz/create-empty/', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                     'X-CSRFToken': csrfToken
//                 },
//                 body: JSON.stringify({
//                     project_owner: projectOwner,
//                     project_slug: projectSlug,
//                     figure_name: figureName,
//                     canvas_size: { width_mm: 170, height_mm: 120 }
//                 })
//             });
// 
//             if (!response.ok) {
//                 const error = await response.json();
//                 console.error('[CanvasTabManager] Failed to create figz bundle:', error);
//                 return null;
//             }
// 
//             const result = await response.json();
//             console.log('[CanvasTabManager] Created figz bundle:', result.directory_path);
// 
//             // Notify callback (e.g., to refresh file tree)
//             if (this.onBundleCreated && result.directory_path) {
//                 this.onBundleCreated(figureName, result.directory_path);
//             }
// 
//             return result.directory_path;
//         } catch (error) {
//             console.error('[CanvasTabManager] Error creating figz bundle:', error);
//             return null;
//         }
//     }
// 
//     /**
//      * Get CSRF token from cookie
//      */
//     private getCSRFToken(): string {
//         const cookies = document.cookie.split(';');
//         for (const cookie of cookies) {
//             const [name, value] = cookie.trim().split('=');
//             if (name === 'csrftoken') {
//                 return value;
//             }
//         }
//         return '';
//     }
// 
//     /**
//      * Create a new figure tab
//      * Prevents duplicate figure names by adding numeric suffix
//      */
//     public createTab(figureName?: string, figurePath?: string): string {
//         const id = `canvas-tab-${Date.now()}`;
// 
//         // Auto-generate unique figure name or sanitize provided name
//         let figName = figureName
//             ? this.sanitizeFigureName(figureName)
//             : this.generateUniqueFigureName();
// 
//         // Check for duplicate names (case-insensitive)
//         const existingNames = this.tabs.map(t => t.figureName.toLowerCase());
//         if (existingNames.includes(figName.toLowerCase())) {
//             // Find next available number
//             let counter = 2;
//             const baseName = figName.replace(/\d+$/, '');  // Remove trailing numbers
//             while (existingNames.includes(`${baseName}${counter}`.toLowerCase())) {
//                 counter++;
//             }
//             figName = `${baseName}${counter}`;  // No space
//         }
// 
//         const newTab: CanvasTab = {
//             id,
//             figureName: figName,
//             figurePath: figurePath,
//             isActive: false
//         };
//         this.tabs.push(newTab);
//         this.renderTabs();
// 
//         // Persist updated tabs to storage
//         this.saveTabsToStorage();
// 
//         return id;
//     }
// 
//     /**
//      * Generate a unique figure name based on existing tabs
//      * Uses no spaces (e.g., "Figure1", "Figure2") for filesystem compatibility
//      */
//     private generateUniqueFigureName(): string {
//         const existingNames = this.tabs.map(t => t.figureName.toLowerCase());
//         let counter = 1;
//         // No space between Figure and number (filesystem-friendly)
//         while (existingNames.includes(`figure${counter}`.toLowerCase()) ||
//                existingNames.includes(`figure ${counter}`.toLowerCase())) {
//             counter++;
//         }
//         return `Figure${counter}`;
//     }
// 
//     /**
//      * Sanitize figure name for filesystem compatibility
//      * Removes/replaces characters that are invalid in filenames
//      */
//     private sanitizeFigureName(name: string): string {
//         return name
//             .replace(/\s+/g, '')           // Remove all spaces
//             .replace(/[<>:"/\\|?*]/g, '')  // Remove invalid filename chars
//             .trim();
//     }
// 
//     /**
//      * Find a tab by figure path
//      */
//     public findTabByFigurePath(figurePath: string): CanvasTab | undefined {
//         // Normalize path for comparison (remove .figz extension to get base)
//         const normalizePath = (p: string) => p.replace(/\.figz$/, '');
//         const normalizedInput = normalizePath(figurePath);
// 
//         return this.tabs.find(tab => {
//             if (!tab.figurePath) return false;
//             return normalizePath(tab.figurePath) === normalizedInput;
//         });
//     }
// 
//     /**
//      * Create or switch to a tab for a figz bundle file
//      * If a tab already exists for this figure, switch to it
//      * Otherwise create a new tab with the figure name
//      */
//     public createTabForFigure(figurePath: string): string {
//         // Check if a tab already exists for this figure
//         const existingTab = this.findTabByFigurePath(figurePath);
//         if (existingTab) {
//             console.log(`[CanvasTabManager] Found existing tab for ${figurePath}, switching to it`);
//             this.switchToTab(existingTab.id);
//             return existingTab.id;
//         }
// 
//         // Extract figure name from path (e.g., "/path/to/Figure1.figz" -> "Figure1")
//         const parts = figurePath.split('/');
//         let filename = parts[parts.length - 1];
//         // Remove .figz extension
//         filename = filename.replace(/\.figz$/, '');
// 
//         return this.createTab(filename, figurePath);
//     }
// 
//     /**
//      * Set figure path for an existing tab (for when canvas is loaded from tree)
//      */
//     public setTabFigurePath(tabId: string, figurePath: string): void {
//         const tab = this.tabs.find(t => t.id === tabId);
//         if (tab) {
//             tab.figurePath = figurePath;
//             this.saveTabsToStorage();
//             console.log(`[CanvasTabManager] Set figurePath for tab ${tabId}: ${figurePath}`);
//         }
//     }
// 
//     /**
//      * Get figure path for the active tab
//      */
//     public getActiveTabFigurePath(): string | undefined {
//         const activeTab = this.getActiveTab();
//         return activeTab?.figurePath;
//     }
// 
//     /**
//      * Switch to a tab
//      */
//     public switchToTab(tabId: string): void {
//         const tab = this.tabs.find(t => t.id === tabId);
//         if (!tab) return;
// 
//         // Don't switch if already active
//         if (this.activeTabId === tabId) return;
// 
//         // Save current canvas state BEFORE switching
//         if (this.onBeforeTabChange) {
//             this.onBeforeTabChange();
//         }
// 
//         this.tabs.forEach(t => t.isActive = false);
//         tab.isActive = true;
//         this.activeTabId = tabId;
//         this.renderTabs();
// 
//         if (this.onTabChange) {
//             this.onTabChange(tabId);
//         }
//     }
// 
//     /**
//      * Close a tab
//      */
//     public closeTab(tabId: string): void {
//         const index = this.tabs.findIndex(t => t.id === tabId);
//         if (index === -1) return;
// 
//         // Don't close if it's the only tab
//         if (this.tabs.length === 1) return;
// 
//         this.tabs.splice(index, 1);
// 
//         // If closing active tab, switch to another
//         if (this.activeTabId === tabId) {
//             const newActiveIndex = Math.min(index, this.tabs.length - 1);
//             this.switchToTab(this.tabs[newActiveIndex].id);
//         } else {
//             this.renderTabs();
//         }
// 
//         // Persist updated tabs to storage
//         this.saveTabsToStorage();
// 
//         if (this.onTabClose) {
//             this.onTabClose(tabId);
//         }
//     }
// 
//     /**
//      * Rename a tab
//      */
//     public renameTab(tabId: string, newName: string): void {
//         const tab = this.tabs.find(t => t.id === tabId);
//         if (!tab) return;
// 
//         tab.figureName = newName;
//         this.renderTabs();
// 
//         // Persist updated tabs to storage
//         this.saveTabsToStorage();
// 
//         if (this.onTabRename) {
//             this.onTabRename(tabId, newName);
//         }
//     }
// 
//     /**
//      * Render dropdown menu items
//      */
//     public renderTabs(): void {
//         const menu = document.getElementById('figure-dropdown-menu');
//         const label = document.getElementById('figure-dropdown-label');
//         if (!menu) return;
// 
//         menu.innerHTML = '';
// 
//         this.tabs.forEach(tab => {
//             const itemElement = this.createDropdownItem(tab);
//             menu.appendChild(itemElement);
//         });
// 
//         // Update the dropdown toggle label to show active tab
//         const activeTab = this.getActiveTab();
//         if (label && activeTab) {
//             label.textContent = activeTab.figureName;
//         }
//     }
// 
//     /**
//      * Create a dropdown item element
//      */
//     private createDropdownItem(tab: CanvasTab): HTMLElement {
//         const item = document.createElement('div');
//         item.className = `figure-dropdown-item${tab.isActive ? ' active' : ''}`;
//         item.dataset.tabId = tab.id;
// 
//         // Icon
//         const icon = document.createElement('i');
//         icon.className = 'fas fa-paint-brush';
//         item.appendChild(icon);
// 
//         // Label
//         const label = document.createElement('span');
//         label.className = 'figure-dropdown-item-label';
//         label.textContent = tab.figureName;
//         item.appendChild(label);
// 
//         // Close button (only show if more than 1 tab)
//         if (this.tabs.length > 1) {
//             const closeBtn = document.createElement('button');
//             closeBtn.className = 'figure-dropdown-item-close';
//             closeBtn.title = 'Close figure';
//             closeBtn.innerHTML = '&times;';
//             closeBtn.onclick = (e) => {
//                 e.stopPropagation();
//                 this.closeTab(tab.id);
//             };
//             item.appendChild(closeBtn);
//         }
// 
//         // Click to switch
//         item.onclick = (e) => {
//             if ((e.target as HTMLElement).classList.contains('figure-dropdown-item-close')) return;
//             this.switchToTab(tab.id);
//             this.closeDropdown();
//         };
// 
//         // Double-click to rename
//         item.ondblclick = (e) => {
//             e.preventDefault();
//             e.stopPropagation();
//             this.startInlineRename(item, tab.id, label);
//         };
// 
//         return item;
//     }
// 
//     /**
//      * Start inline rename in dropdown
//      */
//     private startInlineRename(itemElement: HTMLElement, tabId: string, labelElement: HTMLElement): void {
//         const currentName = labelElement.textContent || '';
// 
//         const input = document.createElement('input');
//         input.type = 'text';
//         input.className = 'figure-rename-input';
//         input.value = currentName;
// 
//         // Create hint tooltip for space-to-underscore conversion
//         const hintTooltip = document.createElement('div');
//         hintTooltip.className = 'rename-hint-tooltip';
//         hintTooltip.textContent = 'Space → _';
//         hintTooltip.style.cssText = 'display:none;position:absolute;background:#6c757d;color:white;padding:2px 6px;border-radius:3px;font-size:11px;z-index:9999;white-space:nowrap;';
// 
//         labelElement.style.display = 'none';
//         itemElement.insertBefore(input, labelElement.nextSibling);
//         itemElement.appendChild(hintTooltip);
//         input.focus();
//         input.select();
// 
//         let isFinished = false;
//         const finishRename = () => {
//             if (isFinished) return;
//             isFinished = true;
//             const newName = input.value.trim() || currentName;
//             this.renameTab(tabId, newName);
//             input.remove();
//             hintTooltip.remove();
//             labelElement.style.display = '';
//         };
// 
//         // Auto-replace spaces with underscores
//         input.addEventListener('beforeinput', (e: InputEvent) => {
//             if (e.data && e.data.includes(' ')) {
//                 e.preventDefault();
//                 // Insert underscore at cursor position
//                 const start = input.selectionStart || 0;
//                 const end = input.selectionEnd || 0;
//                 const replaced = e.data.replace(/\s+/g, '_');
//                 input.value = input.value.slice(0, start) + replaced + input.value.slice(end);
//                 input.setSelectionRange(start + replaced.length, start + replaced.length);
//                 hintTooltip.style.display = 'block';
//                 setTimeout(() => { hintTooltip.style.display = 'none'; }, 1000);
//             }
//         });
// 
//         // Fallback: replace any spaces that got through (e.g., from paste)
//         input.oninput = () => {
//             if (input.value.includes(' ')) {
//                 const pos = input.selectionStart || 0;
//                 const diff = input.value.length - input.value.replace(/\s+/g, '_').length;
//                 input.value = input.value.replace(/\s+/g, '_');
//                 input.setSelectionRange(pos - diff, pos - diff);
//                 hintTooltip.style.display = 'block';
//                 setTimeout(() => { hintTooltip.style.display = 'none'; }, 1000);
//             }
//         };
// 
//         input.onblur = finishRename;
//         input.onkeydown = (e) => {
//             e.stopPropagation();
//             if (e.key === 'Enter') {
//                 e.preventDefault();
//                 finishRename();
//             } else if (e.key === 'Escape') {
//                 e.preventDefault();
//                 input.value = currentName;
//                 finishRename();
//             }
//         };
//     }
// 
//     /**
//      * Toggle dropdown open/close
//      */
//     private toggleDropdown(): void {
//         const container = document.getElementById('figure-dropdown-container');
//         if (container) {
//             container.classList.toggle('open');
//         }
//     }
// 
//     /**
//      * Close dropdown
//      */
//     private closeDropdown(): void {
//         const container = document.getElementById('figure-dropdown-container');
//         if (container) {
//             container.classList.remove('open');
//         }
//     }
// 
//     /**
//      * Get active tab
//      */
//     public getActiveTab(): CanvasTab | null {
//         return this.tabs.find(t => t.id === this.activeTabId) || null;
//     }
// 
//     /**
//      * Get all tabs
//      */
//     public getTabs(): CanvasTab[] {
//         return [...this.tabs];
//     }
// 
//     /**
//      * Get linked data table IDs for a figure
//      */
//     public getLinkedDataTableIds(figureId: string): string[] {
//         const tab = this.tabs.find(t => t.id === figureId);
//         return tab?.linkedDataTableIds || [];
//     }
// 
//     /**
//      * Link a data table to this figure
//      */
//     public linkDataTable(figureId: string, dataTableId: string): void {
//         const tab = this.tabs.find(t => t.id === figureId);
//         if (tab) {
//             if (!tab.linkedDataTableIds) {
//                 tab.linkedDataTableIds = [];
//             }
//             if (!tab.linkedDataTableIds.includes(dataTableId)) {
//                 tab.linkedDataTableIds.push(dataTableId);
//                 this.saveTabsToStorage();
//             }
//         }
//     }
// 
//     /**
//      * Unlink a data table from this figure
//      */
//     public unlinkDataTable(figureId: string, dataTableId: string): void {
//         const tab = this.tabs.find(t => t.id === figureId);
//         if (tab && tab.linkedDataTableIds) {
//             const index = tab.linkedDataTableIds.indexOf(dataTableId);
//             if (index !== -1) {
//                 tab.linkedDataTableIds.splice(index, 1);
//                 this.saveTabsToStorage();
//             }
//         }
//     }
// 
//     /**
//      * Save canvas state to the active tab
//      * Called before switching tabs to preserve current canvas content
//      */
//     public saveCanvasState(canvasJson: any, viewState?: { zoom: number; panX: number; panY: number }): void {
//         const activeTab = this.tabs.find(t => t.id === this.activeTabId);
//         if (activeTab) {
//             activeTab.canvasJson = canvasJson;
//             if (viewState) {
//                 activeTab.viewState = viewState;
//             }
//             console.log(`[CanvasTabManager] Saved state for tab: ${activeTab.figureName}`);
//             // Persist to localStorage
//             this.saveTabsToStorage();
//         }
//     }
// 
//     /**
//      * Get canvas state for a specific tab
//      */
//     public getTabState(tabId: string): { canvasJson?: any; viewState?: { zoom: number; panX: number; panY: number } } | null {
//         const tab = this.tabs.find(t => t.id === tabId);
//         if (!tab) return null;
//         return {
//             canvasJson: tab.canvasJson,
//             viewState: tab.viewState
//         };
//     }
// 
//     /**
//      * Get a tab by ID
//      */
//     public getTab(tabId: string): CanvasTab | undefined {
//         return this.tabs.find(t => t.id === tabId);
//     }
// 
//     /**
//      * Save all tabs to localStorage for persistence across page reloads
//      */
//     private saveTabsToStorage(): void {
//         try {
//             const tabsData = this.tabs.map(tab => ({
//                 id: tab.id,
//                 figureName: tab.figureName,
//                 figurePath: tab.figurePath,
//                 isActive: tab.isActive,
//                 canvasJson: tab.canvasJson,
//                 viewState: tab.viewState
//             }));
//             localStorage.setItem('scitex-vis-canvas-tabs', JSON.stringify(tabsData));
//         } catch (err) {
//             console.warn('[CanvasTabManager] Failed to save tabs to storage:', err);
//         }
//     }
// 
//     /**
//      * Load tabs from localStorage
//      */
//     public loadTabsFromStorage(): boolean {
//         try {
//             const saved = localStorage.getItem('scitex-vis-canvas-tabs');
//             if (saved) {
//                 const tabsData = JSON.parse(saved);
//                 if (Array.isArray(tabsData) && tabsData.length > 0) {
//                     this.tabs = tabsData;
//                     this.activeTabId = tabsData.find((t: CanvasTab) => t.isActive)?.id || tabsData[0].id;
//                     console.log(`[CanvasTabManager] Loaded ${this.tabs.length} tabs from storage`);
//                     return true;
//                 }
//             }
//         } catch (err) {
//             console.warn('[CanvasTabManager] Failed to load tabs from storage:', err);
//         }
//         return false;
//     }
// 
//     /**
//      * Validate tabs against filesystem - remove orphan tabs.
//      * Call this when the file tree refreshes or at initialization.
//      *
//      * Removes:
//      * - Tabs with figurePath that no longer exists in filesystem
//      * - Tabs without figurePath (unsaved figures), except default tab
//      *
//      * @param validPaths Array of valid figz paths from the file tree
//      * @returns Number of tabs removed
//      */
//     public validateAndCleanTabs(validPaths: string[]): number {
//         const initialCount = this.tabs.length;
//         const validPathSet = new Set(validPaths.map(p => p.toLowerCase()));
// 
//         this.tabs = this.tabs.filter(tab => {
//             // Always keep the default tab
//             if (tab.id === 'default') return true;
// 
//             // Tabs without figurePath are orphans (unsaved) - remove them
//             if (!tab.figurePath) {
//                 console.log(`[CanvasTabManager] Removing orphan tab (unsaved): ${tab.figureName}`);
//                 return false;
//             }
// 
//             // Check if the figurePath exists in the tree (case-insensitive)
//             const tabPath = tab.figurePath.toLowerCase();
//             const exists = validPathSet.has(tabPath) ||
//                 Array.from(validPathSet).some(vp => tabPath.endsWith(vp) || vp.endsWith(tabPath));
// 
//             if (!exists) {
//                 console.log(`[CanvasTabManager] Removing stale tab: ${tab.figureName} (${tab.figurePath})`);
//             }
//             return exists;
//         });
// 
//         const removedCount = initialCount - this.tabs.length;
// 
//         // Ensure at least one tab exists
//         if (this.tabs.length === 0) {
//             this.initializeDefaultTab();
//             console.log('[CanvasTabManager] No valid tabs - created default tab');
//         }
// 
//         // Update active tab if it was removed
//         if (this.activeTabId && !this.tabs.find(t => t.id === this.activeTabId)) {
//             this.activeTabId = this.tabs[0]?.id || null;
//             this.tabs.forEach(t => t.isActive = t.id === this.activeTabId);
//         }
// 
//         if (removedCount > 0) {
//             this.saveTabsToStorage();
//             this.renderTabs();
//             console.log(`[CanvasTabManager] Removed ${removedCount} orphan/stale tab(s)`);
//         }
// 
//         return removedCount;
//     }
// 
//     /**
//      * Clear all stored tabs (useful when switching projects)
//      */
//     public clearAllTabs(): void {
//         localStorage.removeItem('scitex-vis-canvas-tabs');
//         this.tabs = [];
//         this.activeTabId = null;
//         this.initializeDefaultTab();
//         this.renderTabs();
//         console.log('[CanvasTabManager] Cleared all tabs');
//     }
// 
//     /**
//      * Initialize event listeners for dropdown and new tab button
//      */
//     public initializeEventListeners(): void {
//         // Dropdown toggle
//         const toggleBtn = document.getElementById('figure-dropdown-toggle');
//         if (toggleBtn) {
//             toggleBtn.onclick = (e) => {
//                 e.stopPropagation();
//                 this.toggleDropdown();
//             };
//         }
// 
//         // New figure button
//         const newTabBtn = document.getElementById('canvas-tab-new');
//         if (newTabBtn) {
//             newTabBtn.onclick = () => {
//                 this.showInlineNewTabInput();
//             };
//         }
// 
//         // Close dropdown when clicking outside
//         document.addEventListener('click', (e) => {
//             const container = document.getElementById('figure-dropdown-container');
//             if (container && !container.contains(e.target as Node)) {
//                 this.closeDropdown();
//             }
//         });
// 
//         // Close dropdown on Escape key
//         document.addEventListener('keydown', (e) => {
//             if (e.key === 'Escape') {
//                 this.closeDropdown();
//             }
//         });
//     }
// 
//     /**
//      * Show inline input for creating a new tab (in dropdown menu)
//      */
//     private showInlineNewTabInput(): void {
//         const menu = document.getElementById('figure-dropdown-menu');
//         if (!menu) return;
// 
//         // Open dropdown first
//         const container = document.getElementById('figure-dropdown-container');
//         if (container) {
//             container.classList.add('open');
//         }
// 
//         // Check if input already exists
//         const existingInput = menu.querySelector('.inline-new-tab-input');
//         if (existingInput) {
//             (existingInput as HTMLInputElement).focus();
//             return;
//         }
// 
//         // Create inline input item
//         const inputItem = document.createElement('div');
//         inputItem.className = 'figure-dropdown-item inline-new-tab-wrapper';
// 
//         // Icon
//         const icon = document.createElement('i');
//         icon.className = 'fas fa-paint-brush';
//         inputItem.appendChild(icon);
// 
//         const input = document.createElement('input');
//         input.type = 'text';
//         input.className = 'inline-new-tab-input figure-rename-input';
//         const defaultFigureName = this.generateUniqueFigureName();  // No space (Figure1, Figure2...)
//         input.value = defaultFigureName;
//         input.placeholder = defaultFigureName;
// 
//         // Create hint tooltip for space-to-underscore conversion
//         const hintTooltip = document.createElement('div');
//         hintTooltip.className = 'rename-hint-tooltip';
//         hintTooltip.textContent = 'Space → _';
//         hintTooltip.style.cssText = 'display:none;position:absolute;background:#6c757d;color:white;padding:2px 6px;border-radius:3px;font-size:11px;z-index:9999;white-space:nowrap;';
// 
//         inputItem.appendChild(input);
//         inputItem.appendChild(hintTooltip);
//         menu.appendChild(inputItem);
// 
//         input.focus();
//         input.select();
// 
//         // Flag to prevent double execution from both Enter key and blur event
//         let isFinished = false;
// 
//         const finishCreate = async () => {
//             if (isFinished) return;
//             isFinished = true;
//             const figureName = input.value.trim() || defaultFigureName;
//             inputItem.remove();
// 
//             // Create figz bundle on backend first (using scitex package)
//             const bundlePath = await this.createFigzBundleOnBackend(figureName);
// 
//             // Create the tab with the figure path (if bundle was created)
//             const newTabId = this.createTab(figureName, bundlePath || undefined);
//             this.switchToTab(newTabId);
//             this.closeDropdown();
//         };
// 
//         const cancelCreate = () => {
//             if (isFinished) return;
//             isFinished = true;
//             inputItem.remove();
//         };
// 
//         // Auto-replace spaces with underscores
//         input.addEventListener('beforeinput', (e: InputEvent) => {
//             if (e.data && e.data.includes(' ')) {
//                 e.preventDefault();
//                 // Insert underscore at cursor position
//                 const start = input.selectionStart || 0;
//                 const end = input.selectionEnd || 0;
//                 const replaced = e.data.replace(/\s+/g, '_');
//                 input.value = input.value.slice(0, start) + replaced + input.value.slice(end);
//                 input.setSelectionRange(start + replaced.length, start + replaced.length);
//                 hintTooltip.style.display = 'block';
//                 setTimeout(() => { hintTooltip.style.display = 'none'; }, 1000);
//             }
//         });
// 
//         // Fallback: replace any spaces that got through (e.g., from paste)
//         input.oninput = () => {
//             if (input.value.includes(' ')) {
//                 const pos = input.selectionStart || 0;
//                 const diff = input.value.length - input.value.replace(/\s+/g, '_').length;
//                 input.value = input.value.replace(/\s+/g, '_');
//                 input.setSelectionRange(pos - diff, pos - diff);
//                 hintTooltip.style.display = 'block';
//                 setTimeout(() => { hintTooltip.style.display = 'none'; }, 1000);
//             }
//         };
// 
//         input.onblur = () => {
//             setTimeout(() => {
//                 if (document.activeElement !== input) {
//                     finishCreate();
//                 }
//             }, 100);
//         };
// 
//         input.onkeydown = (e) => {
//             e.stopPropagation();
//             if (e.key === 'Enter') {
//                 e.preventDefault();
//                 finishCreate();
//             } else if (e.key === 'Escape') {
//                 e.preventDefault();
//                 cancelCreate();
//             }
//         };
//     }
// 
//     /**
//      * Setup drag and drop handlers for tab reordering
//      */
//     private setupDragHandlers(tabElement: HTMLElement, tabId: string): void {
//         tabElement.addEventListener('dragstart', (e: DragEvent) => {
//             if (e.dataTransfer) {
//                 e.dataTransfer.effectAllowed = 'move';
//                 e.dataTransfer.setData('text/plain', tabId);
//             }
//             tabElement.classList.add('dragging');
//         });
// 
//         tabElement.addEventListener('dragend', () => {
//             tabElement.classList.remove('dragging');
//             // Remove all drag-over indicators
//             document.querySelectorAll('.data-tab').forEach(el => {
//                 el.classList.remove('drag-over');
//             });
//         });
// 
//         tabElement.addEventListener('dragover', (e: DragEvent) => {
//             e.preventDefault();
//             if (e.dataTransfer) {
//                 e.dataTransfer.dropEffect = 'move';
//             }
//             tabElement.classList.add('drag-over');
//         });
// 
//         tabElement.addEventListener('dragleave', () => {
//             tabElement.classList.remove('drag-over');
//         });
// 
//         tabElement.addEventListener('drop', (e: DragEvent) => {
//             e.preventDefault();
//             tabElement.classList.remove('drag-over');
// 
//             if (e.dataTransfer) {
//                 const draggedId = e.dataTransfer.getData('text/plain');
//                 this.reorderTabs(draggedId, tabId);
//             }
//         });
//     }
// 
//     /**
//      * Reorder tabs by moving draggedId before targetId
//      */
//     private reorderTabs(draggedId: string, targetId: string): void {
//         if (draggedId === targetId) return;
// 
//         const draggedIndex = this.tabs.findIndex(t => t.id === draggedId);
//         const targetIndex = this.tabs.findIndex(t => t.id === targetId);
// 
//         if (draggedIndex === -1 || targetIndex === -1) return;
// 
//         // Remove dragged tab and insert before target
//         const [draggedTab] = this.tabs.splice(draggedIndex, 1);
//         this.tabs.splice(targetIndex, 0, draggedTab);
// 
//         this.renderTabs();
//     }
// }

// =============================================================================
// End of Source Code
// =============================================================================
