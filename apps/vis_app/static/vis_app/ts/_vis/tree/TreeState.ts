/**
 * Tree State Management
 * Handles expand/collapse state persistence and restoration for tree items
 */

export class TreeState {
    private treeContainer: HTMLElement | null = null;
    private readonly STORAGE_KEY = 'vis-tree-expanded-state';

    constructor(treeContainer: HTMLElement | null) {
        this.treeContainer = treeContainer;
    }

    /**
     * Toggle expand/collapse state of a tree item
     */
    public toggleTreeItem(item: HTMLElement): void {
        const toggle = item.querySelector('.tree-toggle') as HTMLElement;
        const children = item.querySelector('.tree-item-children, .tree-group-children') as HTMLElement;

        if (!toggle || !children) return;

        const isExpanded = toggle.classList.contains('fa-chevron-down');
        const itemId = item.getAttribute('data-id');

        if (isExpanded) {
            // Collapse
            toggle.classList.remove('fa-chevron-down');
            toggle.classList.add('fa-chevron-right');
            children.style.display = 'none';

            // Save collapsed state
            if (itemId) {
                this.saveExpandedState(itemId, false);
            }
        } else {
            // Expand
            toggle.classList.remove('fa-chevron-right');
            toggle.classList.add('fa-chevron-down');
            children.style.display = 'block';

            // Save expanded state
            if (itemId) {
                this.saveExpandedState(itemId, true);
            }
        }

        console.log('[TreeState] Tree item toggled');
    }

    /**
     * Expand all tree items
     */
    public expandAll(): void {
        if (!this.treeContainer) return;

        const toggles = this.treeContainer.querySelectorAll('.tree-toggle.fa-chevron-right');
        toggles.forEach(toggle => {
            const parent = toggle.closest('.tree-item, .tree-group') as HTMLElement;
            if (parent) {
                this.toggleTreeItem(parent);
            }
        });

        console.log('[TreeState] Expanded all items');
    }

    /**
     * Collapse all tree items
     */
    public collapseAll(): void {
        if (!this.treeContainer) return;

        const toggles = this.treeContainer.querySelectorAll('.tree-toggle.fa-chevron-down');
        toggles.forEach(toggle => {
            const parent = toggle.closest('.tree-item, .tree-group') as HTMLElement;
            if (parent) {
                this.toggleTreeItem(parent);
            }
        });

        console.log('[TreeState] Collapsed all items');
    }

    /**
     * Save expanded/collapsed state to localStorage
     */
    private saveExpandedState(itemId: string, isExpanded: boolean): void {
        try {
            const state = this.loadExpandedStates();
            state[itemId] = isExpanded;
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
        } catch (e) {
            console.warn('[TreeState] Failed to save expanded state:', e);
        }
    }

    /**
     * Load expanded states from localStorage
     */
    private loadExpandedStates(): { [key: string]: boolean } {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            return stored ? JSON.parse(stored) : {};
        } catch (e) {
            console.warn('[TreeState] Failed to load expanded states:', e);
            return {};
        }
    }

    /**
     * Restore expanded/collapsed states after building tree
     */
    public restoreExpandedStates(): void {
        if (!this.treeContainer) return;

        const states = this.loadExpandedStates();

        // Apply saved states to all items with IDs
        Object.entries(states).forEach(([itemId, isExpanded]) => {
            const item = this.treeContainer!.querySelector(`[data-id="${itemId}"]`) as HTMLElement;
            if (item) {
                const toggle = item.querySelector('.tree-toggle') as HTMLElement;
                const children = item.querySelector('.tree-item-children, .tree-group-children') as HTMLElement;

                if (toggle && children) {
                    if (isExpanded) {
                        // Expand
                        toggle.classList.remove('fa-chevron-right');
                        toggle.classList.add('fa-chevron-down');
                        children.style.display = 'block';
                    } else {
                        // Collapse
                        toggle.classList.remove('fa-chevron-down');
                        toggle.classList.add('fa-chevron-right');
                        children.style.display = 'none';
                    }
                }
            }
        });

        console.log('[TreeState] Restored expanded states from localStorage');
    }

    /**
     * Clear saved tree state from localStorage
     */
    public clearSavedState(): void {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
            console.log('[TreeState] Cleared saved tree state');
        } catch (e) {
            console.warn('[TreeState] Failed to clear saved state:', e);
        }
    }
}
