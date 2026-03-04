/**
 * TableContextMenu - Right-click context menu for data table operations
 *
 * Responsibilities:
 * - Show context menu on right-click anywhere in table
 * - Context-aware options based on click location
 * - Toggle first row as header
 * - Toggle first column as index
 * - Import data file
 * - Other table operations
 */
export class TableContextMenu {
    constructor(callbacks = {}) {
        this.callbacks = callbacks;
        this.menu = null;
        this.containerSelector = '.data-table-container';
        this.state = {
            firstRowIsHeader: true,
            firstColIsIndex: false
        };
        this.boundContextMenuHandler = null;
        this.createMenu();
        this.setupGlobalListeners();
    }
    /**
     * Set container selector
     */
    setContainerSelector(selector) {
        this.containerSelector = selector;
    }
    /**
     * Get current state
     */
    getState() {
        return { ...this.state };
    }
    /**
     * Set state externally (e.g., from saved preferences)
     */
    setState(state) {
        this.state = { ...this.state, ...state };
    }
    /**
     * Create the context menu element
     */
    createMenu() {
        this.menu = document.createElement('div');
        this.menu.className = 'data-table-context-menu';
        this.menu.style.display = 'none';
        this.menu.innerHTML = `
            <div class="context-menu-section">
                <div class="context-menu-item" data-action="toggle-header">
                    <i class="fas fa-heading"></i>
                    <span>First row as header</span>
                    <i class="fas fa-check check-icon"></i>
                </div>
                <div class="context-menu-item" data-action="toggle-index">
                    <i class="fas fa-hashtag"></i>
                    <span>First column as index</span>
                    <i class="fas fa-check check-icon"></i>
                </div>
            </div>
            <div class="context-menu-divider"></div>
            <div class="context-menu-section">
                <div class="context-menu-item" data-action="import-file">
                    <i class="fas fa-file-import"></i>
                    <span>Import data file...</span>
                </div>
            </div>
        `;
        document.body.appendChild(this.menu);
        this.setupMenuListeners();
        this.updateMenuState();
    }
    /**
     * Setup menu item click listeners
     */
    setupMenuListeners() {
        if (!this.menu)
            return;
        this.menu.querySelectorAll('.context-menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = item.dataset.action;
                this.handleAction(action || '');
                this.hide();
            });
        });
    }
    /**
     * Handle menu action
     */
    handleAction(action) {
        switch (action) {
            case 'toggle-header':
                this.state.firstRowIsHeader = !this.state.firstRowIsHeader;
                this.updateMenuState();
                if (this.callbacks.onToggleHeader) {
                    this.callbacks.onToggleHeader(this.state.firstRowIsHeader);
                }
                if (this.callbacks.onRenderTable) {
                    this.callbacks.onRenderTable();
                }
                if (this.callbacks.statusBarCallback) {
                    this.callbacks.statusBarCallback(`First row is now treated as ${this.state.firstRowIsHeader ? 'header' : 'data'}`);
                }
                console.log('[TableContextMenu] First row is header:', this.state.firstRowIsHeader);
                break;
            case 'toggle-index':
                this.state.firstColIsIndex = !this.state.firstColIsIndex;
                this.updateMenuState();
                if (this.callbacks.onToggleIndex) {
                    this.callbacks.onToggleIndex(this.state.firstColIsIndex);
                }
                if (this.callbacks.onRenderTable) {
                    this.callbacks.onRenderTable();
                }
                if (this.callbacks.statusBarCallback) {
                    this.callbacks.statusBarCallback(`First column is now treated as ${this.state.firstColIsIndex ? 'index' : 'data'}`);
                }
                console.log('[TableContextMenu] First column is index:', this.state.firstColIsIndex);
                break;
            case 'import-file':
                if (this.callbacks.onImportFile) {
                    this.callbacks.onImportFile();
                }
                break;
        }
    }
    /**
     * Update menu checkmarks based on state
     */
    updateMenuState() {
        if (!this.menu)
            return;
        const headerItem = this.menu.querySelector('[data-action="toggle-header"]');
        const indexItem = this.menu.querySelector('[data-action="toggle-index"]');
        if (headerItem) {
            headerItem.classList.toggle('active', this.state.firstRowIsHeader);
        }
        if (indexItem) {
            indexItem.classList.toggle('active', this.state.firstColIsIndex);
        }
    }
    /**
     * Setup global listeners for hiding menu
     */
    setupGlobalListeners() {
        // Hide on click outside
        document.addEventListener('click', () => this.hide());
        // Hide on scroll
        document.addEventListener('scroll', () => this.hide(), true);
        // Hide on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape')
                this.hide();
        });
    }
    /**
     * Setup context menu on table container
     */
    setupContextMenu() {
        const container = document.querySelector(this.containerSelector);
        if (!container) {
            console.warn('[TableContextMenu] Container not found:', this.containerSelector);
            return;
        }
        // Remove existing listener if any (prevent duplicates on re-render)
        if (this.boundContextMenuHandler) {
            container.removeEventListener('contextmenu', this.boundContextMenuHandler);
        }
        // Create bound handler - only handle if target is inside our container
        this.boundContextMenuHandler = (e) => {
            const target = e.target;
            const containerEl = document.querySelector(this.containerSelector);
            // Double-check the event target is inside our container
            if (!containerEl?.contains(target)) {
                return; // Not our event, let it propagate
            }
            e.preventDefault();
            e.stopPropagation();
            this.show(e);
        };
        container.addEventListener('contextmenu', this.boundContextMenuHandler);
        console.log('[TableContextMenu] Context menu setup complete for', this.containerSelector);
    }
    /**
     * Show context menu at position
     */
    show(e) {
        if (!this.menu)
            return;
        // Update state before showing
        this.updateMenuState();
        // Get click coordinates
        const x = e.clientX;
        const y = e.clientY;
        // Position off-screen first to measure without flicker
        this.menu.style.left = '-9999px';
        this.menu.style.top = '-9999px';
        this.menu.style.display = 'block';
        // Get actual menu dimensions
        const menuWidth = this.menu.offsetWidth;
        const menuHeight = this.menu.offsetHeight;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        // Calculate position - default to click point
        let left = x;
        let top = y;
        // Adjust if menu would extend beyond right edge
        if (x + menuWidth > viewportWidth - 10) {
            left = x - menuWidth;
            if (left < 10)
                left = 10;
        }
        // Adjust if menu would extend beyond bottom edge
        if (y + menuHeight > viewportHeight - 10) {
            top = y - menuHeight;
            if (top < 10)
                top = 10;
        }
        // Apply final position
        this.menu.style.left = `${left}px`;
        this.menu.style.top = `${top}px`;
        console.log('[TableContextMenu] Showing at', left, top, 'click:', x, y, 'menu:', menuWidth, 'x', menuHeight);
    }
    /**
     * Hide context menu
     */
    hide() {
        if (this.menu) {
            this.menu.style.display = 'none';
        }
    }
    /**
     * Cleanup
     */
    destroy() {
        if (this.menu && this.menu.parentNode) {
            this.menu.parentNode.removeChild(this.menu);
        }
        this.menu = null;
    }
}
//# sourceMappingURL=TableContextMenu.ts.map
