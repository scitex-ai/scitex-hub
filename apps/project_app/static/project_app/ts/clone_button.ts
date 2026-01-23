/**
 * Clone Button Component - GitHub Style
 * Handles dropdown functionality and clipboard operations for repository cloning
 */

/**
 * Copy text to clipboard with visual feedback
 */
function copyToClipboard(elementId: string): void {
    const input = document.getElementById(elementId) as HTMLInputElement;
    if (!input) {
        console.error('[CloneButton] Element not found:', elementId);
        return;
    }

    input.select();
    input.setSelectionRange(0, 99999); // For mobile devices

    // Copy to clipboard
    navigator.clipboard.writeText(input.value).then(function() {
        // Show success feedback with checkmark
        const container = input.closest('.clone-url-container');
        if (!container) return;

        const button = container.querySelector('.clone-copy-btn') as HTMLButtonElement;
        if (!button) return;

        const originalHTML = button.innerHTML;
        button.innerHTML = '<svg aria-hidden="true" height="16" viewBox="0 0 16 16" width="16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>';
        button.classList.add('copied');

        setTimeout(function() {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    }).catch(function(err) {
        console.error('[CloneButton] Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

/**
 * Switch between clone methods (HTTPS, SSH, SciTeX CLI)
 */
function switchCloneMethod(button: HTMLElement): void {
    const targetId = button.dataset.target;
    console.log('[CloneButton] switchCloneMethod called, target:', targetId);

    // Get parent container
    const container = button.closest('.tab-pane');
    if (!container) {
        console.error('[CloneButton] Could not find parent .tab-pane');
        return;
    }

    // Deactivate all tabs and panels
    container.querySelectorAll('.clone-method-tab').forEach(tab => tab.classList.remove('active'));
    container.querySelectorAll('.clone-method-panel').forEach(panel => panel.classList.remove('active'));

    // Activate clicked tab and corresponding panel
    button.classList.add('active');
    const targetPanel = document.getElementById(targetId!);
    if (targetPanel) {
        targetPanel.classList.add('active');
        console.log('[CloneButton] Activated panel:', targetId);
    } else {
        console.error('[CloneButton] Could not find target panel:', targetId);
    }
}

/**
 * Open workspace for this project
 */
function openWorkspace(): void {
    // Redirect to workspace for this project
    window.location.href = '/code/workspace/';
}

/**
 * Initialize dropdown - use pure JavaScript, don't rely on Bootstrap
 */
(function initDropdown() {
    const container = document.querySelector('.git-clone-button-container');
    const dropdownButton = container?.querySelector('.btn-code-success') as HTMLButtonElement;
    const dropdownMenu = container?.querySelector('.dropdown-menu') as HTMLElement;

    if (!dropdownButton || !dropdownMenu) {
        // Elements not in DOM yet, retry
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initDropdown);
        } else {
            setTimeout(initDropdown, 100);
        }
        return;
    }

    // Remove Bootstrap's data-bs-toggle to prevent conflicts
    dropdownButton.removeAttribute('data-bs-toggle');

    let isOpen = false;

    console.log('[CloneButton] Initializing pure JS dropdown');

    // Toggle dropdown on button click
    dropdownButton.addEventListener('click', function(e: MouseEvent) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();

        console.log('[CloneButton] Button clicked, isOpen:', isOpen);

        if (isOpen) {
            closeDropdown();
        } else {
            openDropdown();
        }
    });

    function openDropdown() {
        // Close all other dropdowns first
        document.querySelectorAll('.dropdown-menu.show').forEach(m => {
            if (m !== dropdownMenu) m.classList.remove('show');
        });

        dropdownMenu.classList.add('show');
        dropdownButton.setAttribute('aria-expanded', 'true');
        isOpen = true;
        console.log('[CloneButton] Dropdown opened');

        // Add one-time click listener to close on outside click
        setTimeout(() => {
            document.addEventListener('click', handleOutsideClick);
        }, 10);
    }

    function closeDropdown() {
        dropdownMenu.classList.remove('show');
        dropdownButton.setAttribute('aria-expanded', 'false');
        isOpen = false;
        console.log('[CloneButton] Dropdown closed');
        document.removeEventListener('click', handleOutsideClick);
    }

    function handleOutsideClick(e: MouseEvent) {
        // Don't close if clicking inside the dropdown menu - let all interactions work
        if (dropdownMenu.contains(e.target as Node)) {
            // Only close if clicking a Download ZIP or external link
            const link = (e.target as HTMLElement).closest('a.clone-action-item');
            if (link) {
                closeDropdown();
            }
            return;
        }
        // Don't close if clicking the button (button handler will toggle)
        if (dropdownButton.contains(e.target as Node)) {
            return;
        }
        // Close for any other outside click
        closeDropdown();
    }

    // Close on Escape key
    document.addEventListener('keydown', function(e: KeyboardEvent) {
        if (e.key === 'Escape' && isOpen) {
            closeDropdown();
        }
    });

    // Initialize clone method tab switching (in case inline onclick doesn't work)
    dropdownMenu.querySelectorAll('.clone-method-tab').forEach(function(tab) {
        tab.addEventListener('click', function(e: Event) {
            e.stopPropagation();
            switchCloneMethod(tab as HTMLElement);
        });
    });

    console.log('[CloneButton] Clone method tabs initialized:', dropdownMenu.querySelectorAll('.clone-method-tab').length);
})();

// Export functions for global access
if (typeof window !== 'undefined') {
    (window as any).copyToClipboard = copyToClipboard;
    (window as any).switchCloneMethod = switchCloneMethod;
    (window as any).openWorkspace = openWorkspace;
}
