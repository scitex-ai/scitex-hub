/**
 * Auto Save Manager
 * Handles automatic saving/restoring of canvas state to localStorage
 */

import { JournalPreset, LabelStyle } from '../types';

export interface EditorState {
    canvas: any;
    layout: string;
    preset: JournalPreset | null;
    darkMode: boolean;
    gridEnabled: boolean;
    snapEnabled: boolean;
    labelStyle: LabelStyle;
    zoomLevel: number;
    history: string[];
    historyIndex: number;
    timestamp: string;
}

export class AutoSaveManager {
    private canvas: any;
    private saveKey: string;
    private autoSaveTimer: any = null;
    private getStateCallback: () => Partial<EditorState>;
    private restoreStateCallback?: (state: EditorState) => void;

    constructor(
        canvas: any,
        saveKey: string,
        getStateCallback: () => Partial<EditorState>,
        restoreStateCallback?: (state: EditorState) => void
    ) {
        this.canvas = canvas;
        this.saveKey = saveKey;
        this.getStateCallback = getStateCallback;
        this.restoreStateCallback = restoreStateCallback;
    }

    /**
     * Schedule auto-save with debouncing
     */
    public scheduleAutoSave(): void {
        // Debounce auto-save (wait 2 seconds after last change)
        if (this.autoSaveTimer) {
            clearTimeout(this.autoSaveTimer);
        }

        this.autoSaveTimer = setTimeout(() => {
            this.saveToLocalStorage();
        }, 2000);
    }

    /**
     * Save current state to localStorage
     */
    public saveToLocalStorage(): void {
        if (!this.canvas) return;

        try {
            // Get current state from callback
            const currentState = this.getStateCallback();

            const state: EditorState = {
                canvas: this.canvas.toJSON(['id', 'panelId', 'filename', 'hierarchyId']),
                layout: currentState.layout || '1x1',
                preset: currentState.preset || null,
                darkMode: currentState.darkMode || false,
                gridEnabled: currentState.gridEnabled !== false,
                snapEnabled: currentState.snapEnabled !== false,
                labelStyle: currentState.labelStyle || 'uppercase',
                zoomLevel: currentState.zoomLevel || 1.0,
                history: currentState.history || [],
                historyIndex: currentState.historyIndex || 0,
                timestamp: new Date().toISOString(),
            };

            localStorage.setItem(this.saveKey, JSON.stringify(state));

            // Show save indicator briefly
            this.showSaveIndicator();

            console.log('[AutoSaveManager] Auto-saved to localStorage');
        } catch (e) {
            console.error('[AutoSaveManager] Auto-save failed:', e);
        }
    }

    /**
     * Restore state from localStorage
     */
    public restoreFromLocalStorage(): boolean {
        if (!this.canvas) return false;

        try {
            const saved = localStorage.getItem(this.saveKey);
            if (!saved) {
                console.log('[AutoSaveManager] No saved state found');
                return false;
            }

            const state: EditorState = JSON.parse(saved);

            // Restore canvas
            this.canvas.loadFromJSON(state.canvas, () => {
                this.canvas.renderAll();

                // Call restore callback if provided
                if (this.restoreStateCallback) {
                    this.restoreStateCallback(state);
                }

                const timestamp = new Date(state.timestamp).toLocaleString();
                console.log('[AutoSaveManager] Restored from localStorage:', timestamp);
            });

            return true;
        } catch (e) {
            console.error('[AutoSaveManager] Restore failed:', e);
            return false;
        }
    }

    /**
     * Clear saved state from localStorage
     */
    public clearSavedState(): void {
        try {
            localStorage.removeItem(this.saveKey);
            console.log('[AutoSaveManager] Cleared saved state');
        } catch (e) {
            console.error('[AutoSaveManager] Clear failed:', e);
        }
    }

    /**
     * Check if saved state exists
     */
    public hasSavedState(): boolean {
        try {
            return localStorage.getItem(this.saveKey) !== null;
        } catch (e) {
            console.error('[AutoSaveManager] Check failed:', e);
            return false;
        }
    }

    /**
     * Get saved state info without loading it
     */
    public getSavedStateInfo(): { timestamp: string; size: number } | null {
        try {
            const saved = localStorage.getItem(this.saveKey);
            if (!saved) return null;

            const state: EditorState = JSON.parse(saved);
            return {
                timestamp: new Date(state.timestamp).toLocaleString(),
                size: saved.length,
            };
        } catch (e) {
            console.error('[AutoSaveManager] Get info failed:', e);
            return null;
        }
    }

    /**
     * Show save indicator in UI
     */
    private showSaveIndicator(): void {
        const saveBtn = document.getElementById('save-btn');
        if (saveBtn) {
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = '<i class="fas fa-check"></i> Saved';
            saveBtn.classList.add('btn-success');

            setTimeout(() => {
                saveBtn.innerHTML = originalText;
                saveBtn.classList.remove('btn-success');
            }, 1500);
        }
    }

    /**
     * Cancel pending auto-save
     */
    public cancelPendingSave(): void {
        if (this.autoSaveTimer) {
            clearTimeout(this.autoSaveTimer);
            this.autoSaveTimer = null;
        }
    }
}
