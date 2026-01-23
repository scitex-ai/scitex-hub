/**
 * Tree Manager for Hierarchical Figure/Axes/Plots structure
 *
 * REFACTORED: Now delegates to 3 focused modules:
 * - TreeState: Expand/collapse state management and localStorage
 * - TreeInteraction: Selection, actions, and event handling
 * - TreeBuilder: HTML element creation for tree structure
 */

import type { Figure } from './types.ts';
import { TreeState } from './tree/TreeState.ts';
import { TreeInteraction } from './tree/TreeInteraction.ts';
import { TreeBuilder } from './tree/TreeBuilder.ts';

export class TreeManager {
    private treeContainer: HTMLElement | null = null;

    // Module instances
    private treeState: TreeState;
    private treeInteraction: TreeInteraction;
    private treeBuilder: TreeBuilder;

    constructor() {
        this.initialize();
    }

    /**
     * Initialize tree interactions
     */
    private initialize(): void {
        this.treeContainer = document.getElementById('figures-tree');
        if (!this.treeContainer) {
            console.warn('[TreeManager] Tree container not found');
            return;
        }

        // Initialize TreeState module
        this.treeState = new TreeState(this.treeContainer);

        // Initialize TreeInteraction module
        this.treeInteraction = new TreeInteraction(
            this.treeContainer,
            (item: HTMLElement) => this.treeState.toggleTreeItem(item)
        );

        // Initialize TreeBuilder module
        this.treeBuilder = new TreeBuilder(
            this.treeContainer,
            () => this.treeState.restoreExpandedStates()
        );

        console.log('[TreeManager] Initialized with modular architecture');
    }

    // ========================================
    // PUBLIC API - Tree Selection
    // ========================================

    public selectItem(item: HTMLElement): void {
        this.treeInteraction?.selectItem(item);
    }

    public selectItemById(itemId: string): void {
        this.treeInteraction?.selectItemById(itemId);
    }

    // ========================================
    // PUBLIC API - Tree State
    // ========================================

    public expandAll(): void {
        this.treeState?.expandAll();
    }

    public collapseAll(): void {
        this.treeState?.collapseAll();
    }

    public clearSavedState(): void {
        this.treeState?.clearSavedState();
    }

    // ========================================
    // PUBLIC API - Tree Building
    // ========================================

    public buildTree(figures: Figure[]): void {
        this.treeBuilder?.buildTree(figures);
    }
}
