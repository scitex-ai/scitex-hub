/**
 * Tests for apps/figrecipe_app/static/figrecipe_app/ts/vis/ui/DataTabManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/figrecipe_app/static/figrecipe_app/ts/vis/ui/DataTabManager';

describe('DataTabManager', () => {
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
// Source: apps/figrecipe_app/static/figrecipe_app/ts/vis/ui/DataTabManager.ts
// =============================================================================

// /**
//  * DataTabManager - Manages tabs for data tables (line objects)
//  *
//  * Responsibilities:
//  * - Tab creation and management
//  * - Tab switching
//  * - Tab close functionality
//  * - Inline rename on double-click
//  */
//
// export interface DataTab {
//     id: string;
//     name: string;
//     /** ID of the linked figure (canvas tab) - bidirectional link */
//     linkedFigureId?: string;
//     figureName?: string;  // Figure name for tab display (deprecated, use linkedFigureId)
//     objectName?: string;  // Object name for tab display (line, scatter, etc.)
//     type: 'line' | 'scatter' | 'categorical' | 'distribution' | 'statistical' | 'grid' | 'area' | 'contour' | 'vector' | 'special' | 'default';
//     isActive: boolean;
//     data?: any;
// }
//
// export class DataTabManager {
//     private tabs: DataTab[] = [];
//     private activeTabId: string | null = null;
//     private onTabChange: ((tabId: string) => void) | null = null;
//     private onTabClose: ((tabId: string) => void) | null = null;
//     private onTabRename: ((tabId: string, newName: string) => void) | null = null;
//
//     constructor() {
//         this.initializeDefaultTab();
//     }
//
//     /**
//      * Initialize with a default tab
//      */
//     private initializeDefaultTab(): void {
//         const defaultTab: DataTab = {
//             id: 'default-data',
//             name: 'Table1',  // No space for filesystem compatibility
//             linkedFigureId: 'default',  // Links to default canvas figure
//             objectName: 'Table1',
//             type: 'default',
//             isActive: true
//         };
//         this.tabs.push(defaultTab);
//         this.activeTabId = 'default-data';
//     }
//
//     /**
//      * Sanitize name for filesystem compatibility
//      */
//     private sanitizeName(name: string): string {
//         return name.replace(/\s+/g, '').replace(/[<>:"/\\|?*]/g, '');
//     }
//
//     /**
//      * Set callbacks
//      */
//     public setCallbacks(
//         onTabChange: (tabId: string) => void,
//         onTabClose: (tabId: string) => void,
//         onTabRename: (tabId: string, newName: string) => void
//     ): void {
//         this.onTabChange = onTabChange;
//         this.onTabClose = onTabClose;
//         this.onTabRename = onTabRename;
//     }
//
//     /**
//      * Create a new tab
//      * Names are sanitized (no spaces) for filesystem compatibility
//      */
//     public createTab(
//         name: string,
//         type: DataTab['type'] = 'default',
//         figureName?: string,
//         objectName?: string,
//         data?: any
//     ): string {
//         const id = `tab-${Date.now()}`;
//
//         // Sanitize name for filesystem compatibility
//         const sanitizedName = this.sanitizeName(name);
//         const sanitizedObjectName = objectName ? this.sanitizeName(objectName) : sanitizedName;
//         const sanitizedFigureName = figureName ? this.sanitizeName(figureName) : undefined;
//
//         const newTab: DataTab = {
//             id,
//             name: sanitizedName,
//             figureName: sanitizedFigureName,
//             objectName: sanitizedObjectName,
//             type,
//             isActive: false,
//             data
//         };
//         this.tabs.push(newTab);
//         this.renderTabs();
//         return id;
//     }
//
//     /**
//      * Create a new tab and switch to it
//      */
//     public createAndSwitchToTab(
//         name: string,
//         type: DataTab['type'] = 'line',
//         figureName?: string,
//         objectName?: string,
//         data?: any
//     ): string {
//         const tabId = this.createTab(name, type, figureName, objectName, data);
//         this.switchToTab(tabId);
//         return tabId;
//     }
//
//     /**
//      * Get tab data by ID
//      */
//     public getTabData(tabId: string): any {
//         const tab = this.tabs.find(t => t.id === tabId);
//         return tab?.data;
//     }
//
//     /**
//      * Update tab data
//      */
//     public updateTabData(tabId: string, data: any): void {
//         const tab = this.tabs.find(t => t.id === tabId);
//         if (tab) {
//             tab.data = data;
//         }
//     }
//
//     /**
//      * Switch to a tab
//      */
//     public switchToTab(tabId: string): void {
//         const tab = this.tabs.find(t => t.id === tabId);
//         if (!tab) return;
//
//         this.tabs.forEach(t => t.isActive = false);
//         tab.isActive = true;
//         this.activeTabId = tabId;
//         this.renderTabs();
//
//         // Scroll to make the active tab visible
//         requestAnimationFrame(() => {
//             this.scrollToActiveTab();
//         });
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
//         tab.name = newName;
//         this.renderTabs();
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
//         const menu = document.getElementById('data-dropdown-menu');
//         const label = document.getElementById('data-dropdown-label');
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
//             label.textContent = activeTab.name;
//         }
//
//         // Update toggle icon based on active tab type
//         const toggleIcon = document.querySelector('#data-dropdown-toggle i:first-child');
//         if (toggleIcon && activeTab) {
//             toggleIcon.className = this.getIconClass(activeTab.type);
//         }
//     }
//
//     /**
//      * Create a dropdown item element
//      */
//     private createDropdownItem(tab: DataTab): HTMLElement {
//         const item = document.createElement('div');
//         item.className = `data-dropdown-item${tab.isActive ? ' active' : ''}`;
//         item.dataset.tabId = tab.id;
//
//         // Icon based on type
//         const icon = document.createElement('i');
//         icon.className = this.getIconClass(tab.type);
//         item.appendChild(icon);
//
//         // Label
//         const label = document.createElement('span');
//         label.className = 'data-dropdown-item-label';
//         label.textContent = tab.name;
//         item.appendChild(label);
//
//         // Close button (only show if more than 1 tab)
//         if (this.tabs.length > 1) {
//             const closeBtn = document.createElement('button');
//             closeBtn.className = 'data-dropdown-item-close';
//             closeBtn.title = 'Close data table';
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
//             if ((e.target as HTMLElement).classList.contains('data-dropdown-item-close')) return;
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
//      * Toggle dropdown open/close
//      */
//     private toggleDropdown(): void {
//         const container = document.getElementById('data-dropdown-container');
//         if (container) {
//             container.classList.toggle('open');
//         }
//     }
//
//     /**
//      * Close dropdown
//      */
//     private closeDropdown(): void {
//         const container = document.getElementById('data-dropdown-container');
//         if (container) {
//             container.classList.remove('open');
//         }
//     }
//
//     /**
//      * Get icon class based on tab type
//      * Icons match the gallery category buttons in canvas pane
//      */
//     private getIconClass(type: DataTab['type']): string {
//         switch (type) {
//             case 'line':
//                 return 'fas fa-chart-line';
//             case 'scatter':
//                 return 'fas fa-braille';
//             case 'categorical':
//                 return 'fas fa-chart-bar';
//             case 'distribution':
//                 return 'fas fa-chart-column';
//             case 'statistical':
//                 return 'fas fa-square-root-variable';
//             case 'grid':
//                 return 'fas fa-th';
//             case 'area':
//                 return 'fas fa-chart-area';
//             case 'contour':
//                 return 'fas fa-layer-group';
//             case 'vector':
//                 return 'fas fa-arrows-alt';
//             case 'special':
//                 return 'fas fa-shapes';
//             default:
//                 return 'fas fa-table';
//         }
//     }
//
//     /**
//      * Start inline rename in dropdown
//      */
//     private startInlineRename(itemElement: HTMLElement, tabId: string, labelElement: HTMLElement): void {
//         const currentName = labelElement.textContent || '';
//
//         // Create wrapper for input and error tooltip
//         const wrapper = document.createElement('div');
//         wrapper.style.position = 'relative';
//         wrapper.style.display = 'inline-block';
//         wrapper.style.flex = '1';
//
//         const input = document.createElement('input');
//         input.type = 'text';
//         input.className = 'data-rename-input';
//         input.value = currentName;
//
//         // Create hint tooltip for space-to-underscore conversion
//         const hintTooltip = document.createElement('div');
//         hintTooltip.className = 'rename-hint-tooltip';
//         hintTooltip.textContent = 'Space → _';
//         hintTooltip.style.cssText = `
//             position: absolute;
//             bottom: 100%;
//             left: 0;
//             background: #6c757d;
//             color: white;
//             padding: 2px 6px;
//             border-radius: 3px;
//             font-size: 11px;
//             white-space: nowrap;
//             display: none;
//             z-index: 1000;
//             margin-bottom: 2px;
//         `;
//
//         wrapper.appendChild(input);
//         wrapper.appendChild(hintTooltip);
//
//         labelElement.style.display = 'none';
//         itemElement.insertBefore(wrapper, labelElement.nextSibling);
//         input.focus();
//         input.select();
//
//         let isFinished = false;
//         const finishRename = () => {
//             if (isFinished) return;
//             isFinished = true;
//             const newName = this.sanitizeName(input.value.trim()) || currentName;
//             this.renameTab(tabId, newName);
//             wrapper.remove();
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
//      * Scroll dropdown menu to make the active tab visible
//      */
//     private scrollToActiveTab(): void {
//         const menu = document.getElementById('data-dropdown-menu');
//         const activeItem = menu?.querySelector('.data-dropdown-item.active') as HTMLElement;
//         if (menu && activeItem) {
//             activeItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
//         }
//     }
//
//     /**
//      * Get active tab
//      */
//     public getActiveTab(): DataTab | null {
//         return this.tabs.find(t => t.id === this.activeTabId) || null;
//     }
//
//     /**
//      * Get all tabs
//      */
//     public getTabs(): DataTab[] {
//         return [...this.tabs];
//     }
//
//     /**
//      * Get tabs linked to a specific figure
//      */
//     public getTabsForFigure(figureId: string): DataTab[] {
//         return this.tabs.filter(t => t.linkedFigureId === figureId);
//     }
//
//     /**
//      * Link a data table to a figure
//      */
//     public linkToFigure(tabId: string, figureId: string): void {
//         const tab = this.tabs.find(t => t.id === tabId);
//         if (tab) {
//             tab.linkedFigureId = figureId;
//         }
//     }
//
//     /**
//      * Unlink a data table from its figure
//      */
//     public unlinkFromFigure(tabId: string): void {
//         const tab = this.tabs.find(t => t.id === tabId);
//         if (tab) {
//             tab.linkedFigureId = undefined;
//         }
//     }
//
//     /**
//      * Validate tabs - remove tabs linked to figures that no longer exist.
//      *
//      * @param validFigureIds Array of valid figure tab IDs
//      * @returns Number of tabs removed
//      */
//     public validateAndCleanTabs(validFigureIds: string[]): number {
//         const initialCount = this.tabs.length;
//         const validIdSet = new Set(validFigureIds);
//
//         this.tabs = this.tabs.filter(tab => {
//             // Keep tabs without linkedFigureId (standalone tables)
//             if (!tab.linkedFigureId) return true;
//
//             // Keep if linked figure still exists
//             const exists = validIdSet.has(tab.linkedFigureId);
//             if (!exists) {
//                 console.log(`[DataTabManager] Removing stale tab: ${tab.name} (linked to ${tab.linkedFigureId})`);
//             }
//             return exists;
//         });
//
//         const removedCount = initialCount - this.tabs.length;
//
//         // Ensure at least one tab exists
//         if (this.tabs.length === 0) {
//             this.initializeDefaultTab();
//             console.log('[DataTabManager] No valid tabs - created default tab');
//         }
//
//         // Update active tab if it was removed
//         if (this.activeTabId && !this.tabs.find(t => t.id === this.activeTabId)) {
//             this.activeTabId = this.tabs[0]?.id || null;
//             this.tabs.forEach(t => t.isActive = t.id === this.activeTabId);
//         }
//
//         if (removedCount > 0) {
//             this.renderTabs();
//             console.log(`[DataTabManager] Removed ${removedCount} stale tab(s)`);
//         }
//
//         return removedCount;
//     }
//
//     /**
//      * Clear all tabs and reset to default
//      */
//     public clearAllTabs(): void {
//         this.tabs = [];
//         this.activeTabId = null;
//         this.initializeDefaultTab();
//         this.renderTabs();
//         console.log('[DataTabManager] Cleared all tabs');
//     }
//
//     /**
//      * Initialize event listeners for dropdown and new tab button
//      */
//     public initializeEventListeners(): void {
//         // Dropdown toggle
//         const toggleBtn = document.getElementById('data-dropdown-toggle');
//         if (toggleBtn) {
//             toggleBtn.onclick = (e) => {
//                 e.stopPropagation();
//                 this.toggleDropdown();
//             };
//         }
//
//         // New data table button
//         const newTabBtn = document.getElementById('data-tab-new');
//         if (newTabBtn) {
//             newTabBtn.onclick = () => {
//                 this.showInlineNewTabInput();
//             };
//         }
//
//         // Close dropdown when clicking outside
//         document.addEventListener('click', (e) => {
//             const container = document.getElementById('data-dropdown-container');
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
//         const menu = document.getElementById('data-dropdown-menu');
//         if (!menu) return;
//
//         // Open dropdown first
//         const container = document.getElementById('data-dropdown-container');
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
//         inputItem.className = 'data-dropdown-item inline-new-tab-wrapper';
//
//         // Icon (table icon for new tables)
//         const icon = document.createElement('i');
//         icon.className = 'fas fa-table';
//         inputItem.appendChild(icon);
//
//         // Create wrapper for input and error tooltip
//         const inputWrapper = document.createElement('div');
//         inputWrapper.style.position = 'relative';
//         inputWrapper.style.display = 'inline-block';
//         inputWrapper.style.flex = '1';
//
//         const input = document.createElement('input');
//         input.type = 'text';
//         input.className = 'inline-new-tab-input data-rename-input';
//         const defaultTableName = `Table${this.tabs.length + 1}`;  // No space for filesystem compatibility
//         input.value = defaultTableName;
//         input.placeholder = defaultTableName;
//
//         // Create hint tooltip for space-to-underscore conversion
//         const hintTooltip = document.createElement('div');
//         hintTooltip.className = 'rename-hint-tooltip';
//         hintTooltip.textContent = 'Space → _';
//         hintTooltip.style.cssText = `
//             position: absolute;
//             bottom: 100%;
//             left: 0;
//             background: #6c757d;
//             color: white;
//             padding: 2px 6px;
//             border-radius: 3px;
//             font-size: 11px;
//             white-space: nowrap;
//             display: none;
//             z-index: 1000;
//             margin-bottom: 2px;
//         `;
//
//         inputWrapper.appendChild(input);
//         inputWrapper.appendChild(hintTooltip);
//         inputItem.appendChild(inputWrapper);
//         menu.appendChild(inputItem);
//
//         input.focus();
//         input.select();
//
//         // Flag to prevent double execution
//         let isFinished = false;
//
//         const finishCreate = () => {
//             if (isFinished) return;
//             isFinished = true;
//             const tableName = this.sanitizeName(input.value.trim()) || defaultTableName;
//             inputItem.remove();
//             // Create table with default type
//             const newTabId = this.createTab(tableName, 'default', undefined, tableName);
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
// }

// =============================================================================
// End of Source Code
// =============================================================================
