/**
 * Tree Interaction Handler
 *
 * Manages user interactions with the tree structure including:
 * - Item selection
 * - Expand/collapse toggles
 * - Action buttons (edit, delete, add)
 */

export interface TreeInteractionCallbacks {
    toggleTreeItem: (item: HTMLElement) => void;
    expandParents: (item: HTMLElement) => void;
}

export class TreeInteraction {
    private treeContainer: HTMLElement;
    private callbacks: TreeInteractionCallbacks;

    constructor(
        treeContainer: HTMLElement,
        callbacks: TreeInteractionCallbacks
    ) {
        this.treeContainer = treeContainer;
        this.callbacks = callbacks;
        this.initialize();
    }

    /**
     * Initialize all tree interactions
     */
    private initialize(): void {
        this.setupTreeSelection();
        this.setupTreeToggles();
        this.setupTreeActions();
        console.log('[TreeInteraction] Initialized');
    }

    /**
     * Setup tree item selection
     */
    private setupTreeSelection(): void {
        // Handle tree item clicks for selection
        this.treeContainer.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;

            // Check if clicked on tree item (not on action buttons or toggles)
            if (target.closest('.tree-action-btn, .tree-add-btn, .tree-toggle')) {
                return; // Ignore clicks on action buttons and toggles
            }

            const item = target.closest('.tree-item') as HTMLElement;
            if (item && item.hasAttribute('data-id')) {
                this.selectItem(item);
            }
        });
    }

    /**
     * Setup expand/collapse toggles for tree items
     */
    private setupTreeToggles(): void {
        // Handle tree toggle clicks (chevrons)
        this.treeContainer.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;

            // Check if clicked on toggle icon or header
            const toggle = target.closest('.tree-toggle') as HTMLElement;
            const header = target.closest('.tree-item-header, .tree-group-header') as HTMLElement;

            if (toggle || (header && !target.closest('.tree-action-btn, .tree-add-btn'))) {
                e.stopPropagation();
                const parent = header?.closest('.tree-item, .tree-group') as HTMLElement;
                if (parent) {
                    this.callbacks.toggleTreeItem(parent);
                }
            }
        });
    }

    /**
     * Setup action buttons (edit, delete, add)
     */
    private setupTreeActions(): void {
        // Handle action button clicks
        this.treeContainer.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;
            const btn = target.closest('.tree-action-btn, .tree-add-btn') as HTMLElement;

            if (btn) {
                e.stopPropagation();
                this.handleTreeAction(btn);
            }
        });
    }

    /**
     * Handle tree action button clicks
     */
    private handleTreeAction(btn: HTMLElement): void {
        const icon = btn.querySelector('i');
        const item = btn.closest('.tree-item, .tree-group, .tree-section') as HTMLElement;
        const label = item?.querySelector('.tree-label')?.textContent || 'item';

        if (!icon) return;

        if (icon.classList.contains('fa-edit')) {
            console.log('[TreeInteraction] Edit requested for:', label);
            this.editItem(item);
        } else if (icon.classList.contains('fa-trash')) {
            console.log('[TreeInteraction] Delete requested for:', label);
            this.deleteItem(item);
        } else if (icon.classList.contains('fa-plus')) {
            console.log('[TreeInteraction] Add requested in:', label);
            this.addItem(item);
        }
    }

    /**
     * Edit item
     */
    private editItem(item: HTMLElement): void {
        const label = item.querySelector('.tree-label')?.textContent || '';
        const itemId = item.getAttribute('data-id') || '';

        // Determine item type
        let itemType = 'item';
        if (item.classList.contains('tree-figure')) itemType = 'figure';
        else if (item.classList.contains('tree-axis')) itemType = 'axis';
        else if (item.classList.contains('tree-plot')) itemType = 'plot';
        else if (item.classList.contains('tree-guide')) itemType = 'guide';
        else if (item.classList.contains('tree-annotation')) itemType = 'annotation';

        console.log('[TreeInteraction] Edit requested:', { itemType, itemId, label });

        // Dispatch custom event for parent component to handle
        const editEvent = new CustomEvent('tree-item-edit', {
            detail: { itemType, itemId, label, element: item },
            bubbles: true
        });
        item.dispatchEvent(editEvent);
    }

    /**
     * Delete item
     */
    private deleteItem(item: HTMLElement): void {
        const label = item.querySelector('.tree-label')?.textContent || '';
        const itemId = item.getAttribute('data-id') || '';

        // Determine item type
        let itemType = 'item';
        if (item.classList.contains('tree-figure')) itemType = 'figure';
        else if (item.classList.contains('tree-axis')) itemType = 'axis';
        else if (item.classList.contains('tree-plot')) itemType = 'plot';
        else if (item.classList.contains('tree-guide')) itemType = 'guide';
        else if (item.classList.contains('tree-annotation')) itemType = 'annotation';

        if (confirm(`Delete ${itemType} "${label}"?\n\nThis action cannot be undone.`)) {
            console.log('[TreeInteraction] Delete requested:', { itemType, itemId, label });

            // Dispatch custom event for parent component to handle
            const deleteEvent = new CustomEvent('tree-item-delete', {
                detail: { itemType, itemId, label, element: item },
                bubbles: true
            });
            item.dispatchEvent(deleteEvent);

            // Remove from DOM (can be prevented by event handler if needed)
            item.remove();
        }
    }

    /**
     * Add item
     */
    private addItem(parent: HTMLElement): void {
        const label = parent.querySelector('.tree-label')?.textContent || 'section';
        const parentId = parent.getAttribute('data-id') || '';

        // Determine parent type and what can be added
        let parentType = 'section';
        let addableTypes: string[] = [];

        if (parent.classList.contains('tree-section')) {
            parentType = 'figures-section';
            addableTypes = ['figure'];
        } else if (parent.classList.contains('tree-figure')) {
            parentType = 'figure';
            addableTypes = ['axis'];
        } else if (parent.classList.contains('tree-axis')) {
            parentType = 'axis';
            addableTypes = ['plot', 'guide', 'annotation'];
        } else if (parent.classList.contains('tree-plots')) {
            parentType = 'plots-group';
            addableTypes = ['plot'];
        } else if (parent.classList.contains('tree-guides')) {
            parentType = 'guides-group';
            addableTypes = ['guide'];
        } else if (parent.classList.contains('tree-annotations')) {
            parentType = 'annotations-group';
            addableTypes = ['annotation'];
        }

        console.log('[TreeInteraction] Add requested:', { parentType, parentId, label, addableTypes });

        // Dispatch custom event for parent component to handle
        const addEvent = new CustomEvent('tree-item-add', {
            detail: { parentType, parentId, label, addableTypes, element: parent },
            bubbles: true
        });
        parent.dispatchEvent(addEvent);
    }

    /**
     * Select a tree item
     */
    public selectItem(item: HTMLElement): void {
        // Remove previous selection from any header
        const previousSelected = this.treeContainer.querySelector('.tree-item-header.selected');
        previousSelected?.classList.remove('selected');

        // Add selection to the clicked item's header only
        const header = item.querySelector('.tree-item-header') as HTMLElement;
        if (header) {
            header.classList.add('selected');
        }

        const label = item.querySelector('.tree-label')?.textContent || '';
        const itemId = item.getAttribute('data-id') || '';

        console.log('[TreeInteraction] Selected:', label);

        // Dispatch selection event for canvas synchronization
        const selectEvent = new CustomEvent('tree-item-select', {
            detail: { itemId, label, element: item },
            bubbles: true
        });
        item.dispatchEvent(selectEvent);
    }

    /**
     * Select tree item by ID (for canvas → tree synchronization)
     */
    public selectItemById(itemId: string): void {
        const item = this.treeContainer.querySelector(`[data-id="${itemId}"]`) as HTMLElement;
        if (item) {
            this.selectItem(item);

            // Expand parent nodes to make item visible
            this.callbacks.expandParents(item);

            // Scroll into view
            item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    /**
     * Expand all parent nodes of an item
     */
    private expandParents(item: HTMLElement): void {
        let parent = item.parentElement;

        while (parent && parent !== this.treeContainer) {
            if (parent.classList.contains('tree-item-children') ||
                parent.classList.contains('tree-group-children')) {
                // Find the parent item/group
                const parentItem = parent.closest('.tree-item, .tree-group') as HTMLElement;
                if (parentItem) {
                    const toggle = parentItem.querySelector('.tree-toggle') as HTMLElement;
                    const children = parentItem.querySelector('.tree-item-children, .tree-group-children') as HTMLElement;

                    if (toggle && children && toggle.classList.contains('fa-chevron-right')) {
                        // Expand if collapsed
                        toggle.classList.remove('fa-chevron-right');
                        toggle.classList.add('fa-chevron-down');
                        children.style.display = 'block';
                    }
                }
            }
            parent = parent.parentElement;
        }
    }
}
