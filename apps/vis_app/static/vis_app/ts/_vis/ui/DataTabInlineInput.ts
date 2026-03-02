/**
 * DataTabInlineInput - Inline input handling for data tabs
 *
 * Responsibilities:
 * - Inline rename input in dropdown menu
 * - Inline new tab input creation
 * - Space-to-underscore conversion with tooltip
 *
 * Extracted from DataTabManager.ts for single responsibility.
 */

/**
 * Create a hint tooltip for space-to-underscore conversion
 */
export function createHintTooltip(): HTMLDivElement {
    const tooltip = document.createElement('div');
    tooltip.className = 'rename-hint-tooltip';
    tooltip.textContent = 'Space → _';
    tooltip.style.cssText = `
        position: absolute;
        bottom: 100%;
        left: 0;
        background: #6c757d;
        color: white;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 11px;
        white-space: nowrap;
        display: none;
        z-index: 1000;
        margin-bottom: 2px;
    `;
    return tooltip;
}

/**
 * Setup space-to-underscore conversion on an input element
 */
export function setupSpaceConversion(input: HTMLInputElement, tooltip: HTMLDivElement): void {
    // Auto-replace spaces with underscores on input
    input.addEventListener('beforeinput', (e: InputEvent) => {
        if (e.data && e.data.includes(' ')) {
            e.preventDefault();
            const start = input.selectionStart || 0;
            const end = input.selectionEnd || 0;
            const replaced = e.data.replace(/\s+/g, '_');
            input.value = input.value.slice(0, start) + replaced + input.value.slice(end);
            input.setSelectionRange(start + replaced.length, start + replaced.length);
            showTooltipBriefly(tooltip);
        }
    });

    // Fallback: replace any spaces that got through (e.g., from paste)
    input.oninput = () => {
        if (input.value.includes(' ')) {
            const pos = input.selectionStart || 0;
            const diff = input.value.length - input.value.replace(/\s+/g, '_').length;
            input.value = input.value.replace(/\s+/g, '_');
            input.setSelectionRange(pos - diff, pos - diff);
            showTooltipBriefly(tooltip);
        }
    };
}

/**
 * Show tooltip briefly
 */
function showTooltipBriefly(tooltip: HTMLDivElement, duration: number = 1000): void {
    tooltip.style.display = 'block';
    setTimeout(() => { tooltip.style.display = 'none'; }, duration);
}

/**
 * Start inline rename for a dropdown item
 */
export function startInlineRename(
    itemElement: HTMLElement,
    labelElement: HTMLElement,
    currentName: string,
    sanitizeName: (name: string) => string,
    onRename: (newName: string) => void
): void {
    // Create wrapper for input and tooltip
    const wrapper = document.createElement('div');
    wrapper.style.position = 'relative';
    wrapper.style.display = 'inline-block';
    wrapper.style.flex = '1';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'data-rename-input';
    input.value = currentName;

    const tooltip = createHintTooltip();
    wrapper.appendChild(input);
    wrapper.appendChild(tooltip);

    labelElement.style.display = 'none';
    itemElement.insertBefore(wrapper, labelElement.nextSibling);
    input.focus();
    input.select();

    setupSpaceConversion(input, tooltip);

    let isFinished = false;
    const finishRename = () => {
        if (isFinished) return;
        isFinished = true;
        const newName = sanitizeName(input.value.trim()) || currentName;
        wrapper.remove();
        labelElement.style.display = '';
        onRename(newName);
    };

    input.onblur = finishRename;
    input.onkeydown = (e) => {
        e.stopPropagation();
        if (e.key === 'Enter') {
            e.preventDefault();
            finishRename();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            input.value = currentName;
            finishRename();
        }
    };
}

/**
 * Show inline input for creating a new tab
 */
export function showInlineNewTabInput(
    menu: HTMLElement,
    defaultName: string,
    sanitizeName: (name: string) => string,
    onCreate: (name: string) => void,
    onCancel: () => void
): void {
    // Check if input already exists
    const existingInput = menu.querySelector('.inline-new-tab-input');
    if (existingInput) {
        (existingInput as HTMLInputElement).focus();
        return;
    }

    // Create inline input item
    const inputItem = document.createElement('div');
    inputItem.className = 'data-dropdown-item inline-new-tab-wrapper';

    // Icon
    const icon = document.createElement('i');
    icon.className = 'fas fa-table';
    inputItem.appendChild(icon);

    // Wrapper for input and tooltip
    const inputWrapper = document.createElement('div');
    inputWrapper.style.position = 'relative';
    inputWrapper.style.display = 'inline-block';
    inputWrapper.style.flex = '1';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'inline-new-tab-input data-rename-input';
    input.value = defaultName;
    input.placeholder = defaultName;

    const tooltip = createHintTooltip();
    inputWrapper.appendChild(input);
    inputWrapper.appendChild(tooltip);
    inputItem.appendChild(inputWrapper);
    menu.appendChild(inputItem);

    input.focus();
    input.select();

    setupSpaceConversion(input, tooltip);

    let isFinished = false;

    const finishCreate = () => {
        if (isFinished) return;
        isFinished = true;
        const tableName = sanitizeName(input.value.trim()) || defaultName;
        inputItem.remove();
        onCreate(tableName);
    };

    const cancelCreate = () => {
        if (isFinished) return;
        isFinished = true;
        inputItem.remove();
        onCancel();
    };

    input.onblur = () => {
        setTimeout(() => {
            if (document.activeElement !== input) {
                finishCreate();
            }
        }, 100);
    };

    input.onkeydown = (e) => {
        e.stopPropagation();
        if (e.key === 'Enter') {
            e.preventDefault();
            finishCreate();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelCreate();
        }
    };
}
