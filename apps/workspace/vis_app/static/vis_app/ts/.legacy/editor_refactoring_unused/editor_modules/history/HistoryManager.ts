/**
 * History Manager
 * Handles undo/redo functionality for the canvas editor
 */

import { CANVAS_CONSTANTS } from '../types';

export class HistoryManager {
    private history: string[] = [];
    private historyIndex: number = -1;
    private readonly maxHistory: number = CANVAS_CONSTANTS.MAX_HISTORY;
    private canvas: any;
    private onStateChange?: () => void;
    private onGridRestore?: () => void;

    constructor(
        canvas: any,
        options?: {
            onStateChange?: () => void;
            onGridRestore?: () => void;
        }
    ) {
        this.canvas = canvas;
        this.onStateChange = options?.onStateChange;
        this.onGridRestore = options?.onGridRestore;
    }

    /**
     * Save current canvas state to history
     */
    public saveToHistory(): void {
        if (!this.canvas) return;

        const json = JSON.stringify(
            this.canvas.toJSON(['id', 'panelId', 'filename', 'hierarchyId'])
        );

        // Remove states after current index (if we undid and then made changes)
        if (this.historyIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.historyIndex + 1);
        }

        // Add new state
        this.history.push(json);

        // Limit history size
        if (this.history.length > this.maxHistory) {
            this.history.shift();
        } else {
            this.historyIndex++;
        }

        // Notify state changed
        this.onStateChange?.();

        console.log(`[HistoryManager] State saved (${this.historyIndex + 1}/${this.history.length})`);
    }

    /**
     * Undo to previous state
     */
    public undo(): { success: boolean; message: string } {
        if (!this.canvas || this.historyIndex <= 0) {
            return { success: false, message: 'Nothing to undo' };
        }

        this.historyIndex--;
        this.restoreFromHistory(this.historyIndex);

        const redoCount = this.history.length - this.historyIndex - 1;
        return {
            success: true,
            message: `Undo (${redoCount} redo available)`
        };
    }

    /**
     * Redo to next state
     */
    public redo(): { success: boolean; message: string } {
        if (!this.canvas || this.historyIndex >= this.history.length - 1) {
            return { success: false, message: 'Nothing to redo' };
        }

        this.historyIndex++;
        this.restoreFromHistory(this.historyIndex);

        return {
            success: true,
            message: `Redo (${this.historyIndex} undo available)`
        };
    }

    /**
     * Restore canvas from history at specific index
     */
    private restoreFromHistory(index: number): void {
        if (!this.canvas || index < 0 || index >= this.history.length) return;

        const state = this.history[index];
        this.canvas.loadFromJSON(state, () => {
            this.canvas.renderAll();

            // Notify state changed
            this.onStateChange?.();

            // Restore grid if needed
            this.onGridRestore?.();

            console.log(`[HistoryManager] Restored state ${index + 1}/${this.history.length}`);
        });
    }

    /**
     * Check if undo is available
     */
    public canUndo(): boolean {
        return this.historyIndex > 0;
    }

    /**
     * Check if redo is available
     */
    public canRedo(): boolean {
        return this.historyIndex < this.history.length - 1;
    }

    /**
     * Get current history info
     */
    public getHistoryInfo(): {
        currentIndex: number;
        totalStates: number;
        canUndo: boolean;
        canRedo: boolean;
    } {
        return {
            currentIndex: this.historyIndex,
            totalStates: this.history.length,
            canUndo: this.canUndo(),
            canRedo: this.canRedo(),
        };
    }

    /**
     * Get history array (for export/auto-save)
     */
    public getHistory(): string[] {
        return [...this.history];
    }

    /**
     * Get current history index
     */
    public getHistoryIndex(): number {
        return this.historyIndex;
    }

    /**
     * Restore history from saved state (for auto-save restore)
     */
    public restoreHistory(history: string[], index: number): void {
        this.history = [...history];
        this.historyIndex = index;
        this.onStateChange?.();
    }

    /**
     * Clear all history
     */
    public clearHistory(): void {
        this.history = [];
        this.historyIndex = -1;
        this.onStateChange?.();
    }
}
