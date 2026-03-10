/**
 * Search Log Manager
 *
 * Manages the search status panel, including:
 * - Log messages with timestamps
 * - Source status indicators (LEDs)
 * - Progress spinners
 */
export class SearchLogManager {
    constructor() {
        this.logElement = null;
        this.pulseDot = null;
        this.logElement = document.getElementById("searchLog");
        this.pulseDot = document.getElementById("searchPulseDot");
        this.setupKeyboardShortcuts();
    }
    setupKeyboardShortcuts() {
        if (!this.logElement)
            return;
        // Make log element focusable
        this.logElement.setAttribute("tabindex", "0");
        // Ctrl+A to select all text in log when focused
        this.logElement.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "a") {
                e.preventDefault();
                this.selectAllText();
            }
        });
    }
    selectAllText() {
        if (!this.logElement)
            return;
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(this.logElement);
        selection?.removeAllRanges();
        selection?.addRange(range);
    }
    clear() {
        if (this.logElement) {
            this.logElement.textContent = "";
        }
    }
    log(message) {
        if (this.logElement) {
            const timestamp = new Date().toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            });
            this.logElement.textContent += `[${timestamp}] ${message}\n`;
            this.logElement.scrollTop = this.logElement.scrollHeight;
        }
    }
    showSearching() {
        if (this.pulseDot)
            this.pulseDot.style.display = "inline-block";
    }
    hideSearching() {
        if (this.pulseDot)
            this.pulseDot.style.display = "none";
    }
    updateSourceStatus(sourceName, status, count) {
        // Find source item (now integrated into source-item elements)
        const item = document.querySelector(`.source-item[data-source="${sourceName}"]`);
        if (!item)
            return;
        const spinner = item.querySelector(".spinner-border");
        const countEl = item.querySelector(".count");
        // Update LED indicator
        const led = document.querySelector(`.search-led[data-source="${sourceName}"]`);
        if (led)
            led.dataset.status = status;
        // Reset classes
        item.classList.remove("searching", "success", "error");
        switch (status) {
            case "searching":
                item.classList.add("searching");
                if (spinner)
                    spinner.style.display = "inline-block";
                if (countEl)
                    countEl.textContent = "...";
                break;
            case "success":
                item.classList.add("success");
                if (spinner)
                    spinner.style.display = "none";
                if (countEl)
                    countEl.textContent = count?.toString() || "0";
                break;
            case "error":
                item.classList.add("error");
                if (spinner)
                    spinner.style.display = "none";
                if (countEl)
                    countEl.textContent = "ERR";
                break;
            case "idle":
                if (spinner)
                    spinner.style.display = "none";
                if (countEl)
                    countEl.textContent = "";
                break;
        }
    }
    resetAllSources() {
        // Reset source items (integrated status)
        const items = document.querySelectorAll(".source-item[data-source]");
        items.forEach((item) => {
            const el = item;
            el.classList.remove("searching", "success", "error");
            const spinner = el.querySelector(".spinner-border");
            const count = el.querySelector(".count");
            if (spinner)
                spinner.style.display = "none";
            if (count)
                count.textContent = "";
        });
        // Reset all LED indicators
        const leds = document.querySelectorAll(".search-led");
        leds.forEach((led) => {
            led.dataset.status = "idle";
        });
    }
}
// Global singleton instance
export const searchLog = new SearchLogManager();
//# sourceMappingURL=SearchLogManager.ts.map
