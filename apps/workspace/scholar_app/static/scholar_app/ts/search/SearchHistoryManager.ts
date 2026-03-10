/**
 * Search History Manager
 *
 * Manages search query history with localStorage persistence
 * and arrow key navigation in input fields.
 */
export class SearchHistoryManager {
    constructor() {
        this.history = [];
        this.historyIndex = -1;
        this.currentInput = "";
        this.maxHistory = 50;
        this.storageKey = "scitex_search_history";
        this.inputElement = null;
        this.loadFromStorage();
    }
    loadFromStorage() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                this.history = JSON.parse(stored);
            }
        }
        catch (e) {
            console.warn("[SearchHistory] Failed to load history:", e);
            this.history = [];
        }
    }
    saveToStorage() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.history));
        }
        catch (e) {
            console.warn("[SearchHistory] Failed to save history:", e);
        }
    }
    addQuery(query) {
        if (!query.trim())
            return;
        // Remove duplicates
        const index = this.history.indexOf(query);
        if (index !== -1) {
            this.history.splice(index, 1);
        }
        // Add to front
        this.history.unshift(query);
        // Limit history size
        if (this.history.length > this.maxHistory) {
            this.history = this.history.slice(0, this.maxHistory);
        }
        this.saveToStorage();
        this.historyIndex = -1;
    }
    attachToInput(input) {
        this.inputElement = input;
        input.addEventListener("keydown", (e) => {
            if (e.key === "ArrowUp") {
                e.preventDefault();
                this.navigateHistory(1);
            }
            else if (e.key === "ArrowDown") {
                e.preventDefault();
                this.navigateHistory(-1);
            }
            else if (e.key !== "Enter") {
                // Reset index when typing (not Enter)
                this.historyIndex = -1;
                this.currentInput = input.value;
            }
        });
    }
    navigateHistory(direction) {
        if (!this.inputElement || this.history.length === 0)
            return;
        // Save current input if starting navigation
        if (this.historyIndex === -1) {
            this.currentInput = this.inputElement.value;
        }
        // Calculate new index
        const newIndex = this.historyIndex + direction;
        if (newIndex < -1) {
            // Below history, show current input
            this.historyIndex = -1;
            this.inputElement.value = this.currentInput;
        }
        else if (newIndex >= this.history.length) {
            // At end of history, stay there
            return;
        }
        else if (newIndex === -1) {
            // Back to current input
            this.historyIndex = -1;
            this.inputElement.value = this.currentInput;
        }
        else {
            // Navigate in history
            this.historyIndex = newIndex;
            this.inputElement.value = this.history[this.historyIndex];
        }
        // Move cursor to end
        this.inputElement.setSelectionRange(this.inputElement.value.length, this.inputElement.value.length);
    }
    getHistory() {
        return [...this.history];
    }
    clearHistory() {
        this.history = [];
        this.historyIndex = -1;
        this.saveToStorage();
    }
}
// Global singleton instance
export const searchHistory = new SearchHistoryManager();
//# sourceMappingURL=SearchHistoryManager.ts.map
