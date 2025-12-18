/**
 * Scholar Tab Switcher
 * Handles tab navigation and content switching for the Scholar unified page
 */

const TAB_ORDER = ['bibtex', 'search', 'graph'];
const DEFAULT_TAB = 'bibtex';

function getActiveTab(): string {
    const hash = window.location.hash.slice(1);
    return TAB_ORDER.includes(hash) ? hash : DEFAULT_TAB;
}

function switchTab(tabName: string): void {
    // Update tab navigation
    document.querySelectorAll('.scholar-tab').forEach(tab => {
        const tabElement = tab as HTMLElement;
        if (tabElement.dataset.tab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    // Update main content
    document.querySelectorAll('.scholar-tab-content').forEach(content => {
        const contentElement = content as HTMLElement;
        if (contentElement.dataset.tab === tabName) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });

    // Update details panel
    document.querySelectorAll('.scholar-details-content').forEach(content => {
        const contentElement = content as HTMLElement;
        if (contentElement.dataset.tab === tabName) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });

    // Trigger resize for components that need it (like graphs)
    window.dispatchEvent(new Event('resize'));
}

function initTabSwitcher(): void {
    // Handle tab clicks
    document.querySelectorAll('.scholar-tab').forEach(tab => {
        tab.addEventListener('click', function(this: HTMLElement, e: Event) {
            e.preventDefault();
            const tabName = this.dataset.tab;
            if (tabName) {
                window.location.hash = tabName;
                switchTab(tabName);
            }
        });
    });

    // Handle hash changes (back/forward navigation)
    window.addEventListener('hashchange', function() {
        switchTab(getActiveTab());
    });

    // Initial tab activation
    const activeTab = getActiveTab();
    if (!window.location.hash) {
        window.location.hash = DEFAULT_TAB;
    }
    switchTab(activeTab);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTabSwitcher);
} else {
    initTabSwitcher();
}

export { switchTab, getActiveTab, TAB_ORDER, DEFAULT_TAB };
