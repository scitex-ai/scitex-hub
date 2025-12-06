/**
 * Search Controls - Handles filter preferences, sort, and slider initialization
 * for the right panel search controls
 */

// noUiSlider is loaded externally via CDN
declare const noUiSlider: any;

// Local storage key for search preferences
const SEARCH_PREFS_KEY = 'scitex_search_preferences';

interface SearchPreferences {
    sources: Record<string, boolean>;
    yearFrom: string;
    yearTo: string;
    citationsMin: string;
    citationsMax: string;
    impactFactorMin: string;
    impactFactorMax: string;
    sortDirections: Record<string, string>;
    author: string;
    journal: string;
    docType: string;
    language: string;
}

// Toggle collapsible section
function toggleSection(header: HTMLElement): void {
    const section = header.closest('.ctrl-section');
    if (section) {
        section.classList.toggle('expanded');
    }
}

// Toggle sort direction: none -> desc -> asc -> none
function toggleSortDirection(item: HTMLElement): void {
    const current = item.dataset.direction || 'none';
    const dirSpan = item.querySelector('.sort-dir');
    let next: string;

    if (current === 'none') {
        next = 'desc';
        if (dirSpan) dirSpan.innerHTML = '<i class="fas fa-arrow-down"></i>';
    } else if (current === 'desc') {
        next = 'asc';
        if (dirSpan) dirSpan.innerHTML = '<i class="fas fa-arrow-up"></i>';
    } else {
        next = 'none';
        if (dirSpan) dirSpan.innerHTML = '';
    }

    item.dataset.direction = next;
    item.classList.toggle('active', next !== 'none');

    // Update hidden form fields
    updateSortFields();
    savePreferences();
}

// Update hidden sort fields in form
function updateSortFields(): void {
    const container = document.getElementById('dragSortContainer');
    if (!container) return;

    const sortItems = container.querySelectorAll<HTMLElement>('.sort-item');
    const form = document.getElementById('literatureSearchForm');

    // Remove existing sort inputs
    if (form) {
        form.querySelectorAll('input[name^="sort_"]').forEach(el => el.remove());
    }

    // Add new sort inputs based on current state
    sortItems.forEach((item) => {
        const field = item.dataset.field;
        const direction = item.dataset.direction;
        if (direction !== 'none' && form && field) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = `sort_${field}`;
            input.value = direction;
            form.appendChild(input);
        }
    });
}

// Save preferences to localStorage
function savePreferences(): void {
    const prefs: SearchPreferences = {
        sources: {},
        yearFrom: (document.getElementById('yearFromInput') as HTMLInputElement)?.value || '',
        yearTo: (document.getElementById('yearToInput') as HTMLInputElement)?.value || '',
        citationsMin: (document.getElementById('citationsMinInput') as HTMLInputElement)?.value || '',
        citationsMax: (document.getElementById('citationsMaxInput') as HTMLInputElement)?.value || '',
        impactFactorMin: (document.getElementById('impactFactorMinInput') as HTMLInputElement)?.value || '',
        impactFactorMax: (document.getElementById('impactFactorMaxInput') as HTMLInputElement)?.value || '',
        sortDirections: {},
        author: (document.querySelector('input[name="author"]') as HTMLInputElement)?.value || '',
        journal: (document.querySelector('input[name="journal"]') as HTMLInputElement)?.value || '',
        docType: (document.querySelector('select[name="doc_type"]') as HTMLSelectElement)?.value || '',
        language: (document.querySelector('select[name="language"]') as HTMLSelectElement)?.value || '',
    };

    // Collect source states
    document.querySelectorAll<HTMLInputElement>('.source-toggle').forEach(cb => {
        prefs.sources[cb.name] = cb.checked;
    });

    // Collect sort directions
    document.querySelectorAll<HTMLElement>('.sort-item').forEach(item => {
        if (item.dataset.field) {
            prefs.sortDirections[item.dataset.field] = item.dataset.direction || 'none';
        }
    });

    localStorage.setItem(SEARCH_PREFS_KEY, JSON.stringify(prefs));
}

// Load preferences from localStorage
function loadPreferences(): SearchPreferences | null {
    const stored = localStorage.getItem(SEARCH_PREFS_KEY);
    if (!stored) return null;

    try {
        const prefs: SearchPreferences = JSON.parse(stored);

        // Restore sources
        if (prefs.sources) {
            Object.entries(prefs.sources).forEach(([name, checked]) => {
                const cb = document.querySelector<HTMLInputElement>(`input[name="${name}"]`);
                if (cb) cb.checked = checked;
            });
            updateAllSourcesToggle();
        }

        // Restore sort directions
        if (prefs.sortDirections) {
            Object.entries(prefs.sortDirections).forEach(([field, dir]) => {
                const item = document.querySelector<HTMLElement>(`.sort-item[data-field="${field}"]`);
                if (item) {
                    item.dataset.direction = dir;
                    const dirSpan = item.querySelector('.sort-dir');
                    if (dir === 'desc') {
                        if (dirSpan) dirSpan.innerHTML = '<i class="fas fa-arrow-down"></i>';
                        item.classList.add('active');
                    } else if (dir === 'asc') {
                        if (dirSpan) dirSpan.innerHTML = '<i class="fas fa-arrow-up"></i>';
                        item.classList.add('active');
                    }
                }
            });
            updateSortFields();
        }

        // Restore advanced fields
        if (prefs.author) {
            const el = document.querySelector<HTMLInputElement>('input[name="author"]');
            if (el) el.value = prefs.author;
        }
        if (prefs.journal) {
            const el = document.querySelector<HTMLInputElement>('input[name="journal"]');
            if (el) el.value = prefs.journal;
        }
        if (prefs.docType) {
            const el = document.querySelector<HTMLSelectElement>('select[name="doc_type"]');
            if (el) el.value = prefs.docType;
        }
        if (prefs.language) {
            const el = document.querySelector<HTMLSelectElement>('select[name="language"]');
            if (el) el.value = prefs.language;
        }

        return prefs;
    } catch (e) {
        console.warn('Failed to load search preferences:', e);
        return null;
    }
}

// Update "All" toggle based on individual sources
function updateAllSourcesToggle(): void {
    const allToggle = document.getElementById('source_all_toggle') as HTMLInputElement | null;
    const sourceToggles = document.querySelectorAll<HTMLInputElement>('.source-toggle');
    if (allToggle && sourceToggles.length) {
        const allChecked = Array.from(sourceToggles).every(cb => cb.checked);
        allToggle.checked = allChecked;
    }
}

// Initialize sliders
function initSliders(prefs: SearchPreferences | null): void {
    // Year slider
    const yearSlider = document.getElementById('yearSlider') as HTMLElement & { noUiSlider?: noUiSlider.API };
    if (yearSlider && typeof noUiSlider !== 'undefined') {
        const yearMin = parseInt(yearSlider.dataset.min || '1900');
        const yearMax = parseInt(yearSlider.dataset.max || '2025');
        const yearFromVal = prefs?.yearFrom ? parseInt(prefs.yearFrom) : yearMin;
        const yearToVal = prefs?.yearTo ? parseInt(prefs.yearTo) : yearMax;

        noUiSlider.create(yearSlider, {
            start: [yearFromVal, yearToVal],
            connect: true,
            range: { 'min': yearMin, 'max': yearMax },
            step: 1
        });

        yearSlider.noUiSlider?.on('update', (values: (string | number)[]) => {
            const minDisplay = document.getElementById('yearMinDisplay');
            const maxDisplay = document.getElementById('yearMaxDisplay');
            const minInput = document.getElementById('yearFromInput') as HTMLInputElement;
            const maxInput = document.getElementById('yearToInput') as HTMLInputElement;

            if (minDisplay) minDisplay.textContent = Math.round(Number(values[0])).toString();
            if (maxDisplay) maxDisplay.textContent = Math.round(Number(values[1])).toString();
            if (minInput) minInput.value = Math.round(Number(values[0])).toString();
            if (maxInput) maxInput.value = Math.round(Number(values[1])).toString();
        });
        yearSlider.noUiSlider?.on('change', savePreferences);
    }

    // Citations slider
    const citSlider = document.getElementById('citationsSlider') as HTMLElement & { noUiSlider?: noUiSlider.API };
    if (citSlider && typeof noUiSlider !== 'undefined') {
        const citMax = parseInt(citSlider.dataset.max || '12000');
        const citMinVal = prefs?.citationsMin ? parseInt(prefs.citationsMin) : 0;
        const citMaxVal = prefs?.citationsMax ? parseInt(prefs.citationsMax) : citMax;

        noUiSlider.create(citSlider, {
            start: [citMinVal, citMaxVal],
            connect: true,
            range: { 'min': 0, 'max': citMax },
            step: 100
        });

        citSlider.noUiSlider?.on('update', (values: (string | number)[]) => {
            const minDisplay = document.getElementById('citationsMinDisplay');
            const maxDisplay = document.getElementById('citationsMaxDisplay');
            const minInput = document.getElementById('citationsMinInput') as HTMLInputElement;
            const maxInput = document.getElementById('citationsMaxInput') as HTMLInputElement;

            if (minDisplay) minDisplay.textContent = Math.round(Number(values[0])).toString();
            if (maxDisplay) maxDisplay.textContent = Math.round(Number(values[1])).toString();
            if (minInput) minInput.value = Math.round(Number(values[0])).toString();
            if (maxInput) maxInput.value = Math.round(Number(values[1])).toString();
        });
        citSlider.noUiSlider?.on('change', savePreferences);
    }

    // Impact Factor slider
    const ifSlider = document.getElementById('impactFactorSlider') as HTMLElement & { noUiSlider?: noUiSlider.API };
    if (ifSlider && typeof noUiSlider !== 'undefined') {
        const ifMax = parseFloat(ifSlider.dataset.max || '50.0');
        const ifMinVal = prefs?.impactFactorMin ? parseFloat(prefs.impactFactorMin) : 0;
        const ifMaxVal = prefs?.impactFactorMax ? parseFloat(prefs.impactFactorMax) : ifMax;

        noUiSlider.create(ifSlider, {
            start: [ifMinVal, ifMaxVal],
            connect: true,
            range: { 'min': 0, 'max': ifMax },
            step: 0.5
        });

        ifSlider.noUiSlider?.on('update', (values: (string | number)[]) => {
            const minDisplay = document.getElementById('impactFactorMinDisplay');
            const maxDisplay = document.getElementById('impactFactorMaxDisplay');
            const minInput = document.getElementById('impactFactorMinInput') as HTMLInputElement;
            const maxInput = document.getElementById('impactFactorMaxInput') as HTMLInputElement;

            if (minDisplay) minDisplay.textContent = parseFloat(String(values[0])).toFixed(1);
            if (maxDisplay) maxDisplay.textContent = parseFloat(String(values[1])).toFixed(1);
            if (minInput) minInput.value = parseFloat(String(values[0])).toFixed(1);
            if (maxInput) maxInput.value = parseFloat(String(values[1])).toFixed(1);
        });
        ifSlider.noUiSlider?.on('change', savePreferences);
    }
}

// Initialize search controls
export function initSearchControls(): void {
    // Load saved preferences
    const prefs = loadPreferences();

    // Initialize noUiSlider for filters
    initSliders(prefs);

    // Handle "All" sources toggle
    const allToggle = document.getElementById('source_all_toggle') as HTMLInputElement | null;
    if (allToggle) {
        allToggle.addEventListener('change', function(this: HTMLInputElement) {
            document.querySelectorAll<HTMLInputElement>('.source-toggle').forEach(cb => {
                cb.checked = this.checked;
            });
            savePreferences();
        });
    }

    // Handle individual source toggles
    document.querySelectorAll<HTMLInputElement>('.source-toggle').forEach(cb => {
        cb.addEventListener('change', () => {
            updateAllSourcesToggle();
            savePreferences();
        });
    });

    // Handle advanced field changes
    document.querySelectorAll<HTMLInputElement | HTMLSelectElement>('.adv-field input, .adv-field select').forEach(el => {
        el.addEventListener('change', savePreferences);
        el.addEventListener('input', savePreferences);
    });

    // Bind section toggle handlers
    document.querySelectorAll<HTMLElement>('.ctrl-header').forEach(header => {
        header.addEventListener('click', () => toggleSection(header));
    });

    // Bind sort item handlers
    document.querySelectorAll<HTMLElement>('.sort-item').forEach(item => {
        item.addEventListener('click', () => toggleSortDirection(item));
    });
}

// Keyboard shortcut: Ctrl+K to focus search input
function initKeyboardShortcuts(): void {
    document.addEventListener('keydown', (e: KeyboardEvent) => {
        // Ctrl+K or Cmd+K (Mac)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector<HTMLInputElement>('input[name="q"], .search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });
}

/**
 * Search operators for advanced filtering via query string
 * Supported operators:
 * - t=term - Search in title
 * - a=name - Filter by author
 * - j=name - Filter by journal
 * - ys=YYYY - Year start
 * - ye=YYYY - Year end
 * - cl=N - Citations low (minimum)
 * - ch=N - Citations high (maximum)
 * - ifl=N - Impact factor low (minimum)
 * - ifh=N - Impact factor high (maximum)
 * Example: 'hippocampus t="memory" a="smith" ys=2020 ye=2024 cl=10 ch=1000'
 */
interface ParsedOperators {
    query: string;
    title?: string;
    author?: string;
    journal?: string;
    yearFrom?: number;
    yearTo?: number;
    citationsLow?: number;
    citationsHigh?: number;
    impactFactorLow?: number;
    impactFactorHigh?: number;
}

function parseSearchOperators(input: string): ParsedOperators {
    const result: ParsedOperators = { query: '' };

    // Regular expressions for operators (using = instead of :)
    const patterns = {
        title: /\bt=([^\s]+|"[^"]+"|'[^']+')/gi,
        author: /\ba=([^\s]+|"[^"]+"|'[^']+')/gi,
        journal: /\bj=([^\s]+|"[^"]+"|'[^']+')/gi,
        yearStart: /\bys=(\d{4})/gi,
        yearEnd: /\bye=(\d{4})/gi,
        citationsLow: /\bcl=(\d+)/gi,
        citationsHigh: /\bch=(\d+)/gi,
        impactFactorLow: /\bifl=(\d+(?:\.\d+)?)/gi,
        impactFactorHigh: /\bifh=(\d+(?:\.\d+)?)/gi,
    };

    let remaining = input;

    // Extract title operator
    const titleMatch = patterns.title.exec(input);
    if (titleMatch) {
        result.title = titleMatch[1].replace(/["']/g, '');
        remaining = remaining.replace(titleMatch[0], '');
    }

    // Extract author operator
    patterns.author.lastIndex = 0;
    const authorMatch = patterns.author.exec(input);
    if (authorMatch) {
        result.author = authorMatch[1].replace(/["']/g, '');
        remaining = remaining.replace(authorMatch[0], '');
    }

    // Extract journal operator
    patterns.journal.lastIndex = 0;
    const journalMatch = patterns.journal.exec(input);
    if (journalMatch) {
        result.journal = journalMatch[1].replace(/["']/g, '');
        remaining = remaining.replace(journalMatch[0], '');
    }

    // Extract year start
    patterns.yearStart.lastIndex = 0;
    const ysMatch = patterns.yearStart.exec(input);
    if (ysMatch) {
        result.yearFrom = parseInt(ysMatch[1]);
        remaining = remaining.replace(ysMatch[0], '');
    }

    // Extract year end
    patterns.yearEnd.lastIndex = 0;
    const yeMatch = patterns.yearEnd.exec(input);
    if (yeMatch) {
        result.yearTo = parseInt(yeMatch[1]);
        remaining = remaining.replace(yeMatch[0], '');
    }

    // Extract citations low
    patterns.citationsLow.lastIndex = 0;
    const clMatch = patterns.citationsLow.exec(input);
    if (clMatch) {
        result.citationsLow = parseInt(clMatch[1]);
        remaining = remaining.replace(clMatch[0], '');
    }

    // Extract citations high
    patterns.citationsHigh.lastIndex = 0;
    const chMatch = patterns.citationsHigh.exec(input);
    if (chMatch) {
        result.citationsHigh = parseInt(chMatch[1]);
        remaining = remaining.replace(chMatch[0], '');
    }

    // Extract impact factor low
    patterns.impactFactorLow.lastIndex = 0;
    const iflMatch = patterns.impactFactorLow.exec(input);
    if (iflMatch) {
        result.impactFactorLow = parseFloat(iflMatch[1]);
        remaining = remaining.replace(iflMatch[0], '');
    }

    // Extract impact factor high
    patterns.impactFactorHigh.lastIndex = 0;
    const ifhMatch = patterns.impactFactorHigh.exec(input);
    if (ifhMatch) {
        result.impactFactorHigh = parseFloat(ifhMatch[1]);
        remaining = remaining.replace(ifhMatch[0], '');
    }

    // Clean up remaining query
    result.query = remaining.trim().replace(/\s+/g, ' ');

    return result;
}

/**
 * Apply parsed operators to form fields before search
 */
function applyOperatorsToForm(operators: ParsedOperators): void {
    // Author field
    if (operators.author) {
        const authorInput = document.querySelector<HTMLInputElement>('input[name="author"]');
        if (authorInput) authorInput.value = operators.author;
    }

    // Journal field
    if (operators.journal) {
        const journalInput = document.querySelector<HTMLInputElement>('input[name="journal"]');
        if (journalInput) journalInput.value = operators.journal;
    }

    // Year range sliders
    const yearSlider = document.getElementById('yearSlider') as HTMLElement & { noUiSlider?: noUiSlider.API };
    if (yearSlider?.noUiSlider) {
        const currentMin = parseInt((document.getElementById('yearFromInput') as HTMLInputElement)?.value || '1900');
        const currentMax = parseInt((document.getElementById('yearToInput') as HTMLInputElement)?.value || '2025');
        const yearFrom = operators.yearFrom ?? currentMin;
        const yearTo = operators.yearTo ?? currentMax;
        yearSlider.noUiSlider.set([yearFrom, yearTo]);
    }

    // Citations slider (set low/high)
    const citSlider = document.getElementById('citationsSlider') as HTMLElement & { noUiSlider?: noUiSlider.API };
    if (citSlider?.noUiSlider) {
        const currentMin = parseInt((document.getElementById('citationsMinInput') as HTMLInputElement)?.value || '0');
        const currentMax = parseInt((document.getElementById('citationsMaxInput') as HTMLInputElement)?.value || '128');
        const citLow = operators.citationsLow ?? currentMin;
        const citHigh = operators.citationsHigh ?? currentMax;
        citSlider.noUiSlider.set([citLow, citHigh]);
    }

    // Impact factor slider (set low/high)
    const ifSlider = document.getElementById('impactFactorSlider') as HTMLElement & { noUiSlider?: noUiSlider.API };
    if (ifSlider?.noUiSlider) {
        const currentMin = parseFloat((document.getElementById('impactFactorMinInput') as HTMLInputElement)?.value || '0');
        const currentMax = parseFloat((document.getElementById('impactFactorMaxInput') as HTMLInputElement)?.value || '50');
        const ifLow = operators.impactFactorLow ?? currentMin;
        const ifHigh = operators.impactFactorHigh ?? currentMax;
        ifSlider.noUiSlider.set([ifLow, ifHigh]);
    }
}

/**
 * Initialize search operator parsing on form submit
 */
function initSearchOperators(): void {
    const searchForm = document.getElementById('literatureSearchForm') as HTMLFormElement | null;
    const searchInput = document.querySelector<HTMLInputElement>('input[name="q"]');

    if (searchForm && searchInput) {
        searchForm.addEventListener('submit', (e) => {
            const operators = parseSearchOperators(searchInput.value);

            // Apply operators to form fields
            applyOperatorsToForm(operators);

            // Update search input with clean query (without operators)
            // But keep original if user wants to see what they searched
            if (operators.query !== searchInput.value) {
                // Store original in data attribute for display
                searchInput.dataset.originalQuery = searchInput.value;
            }
        });
    }
}

// Auto-initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    initSearchControls();
    initKeyboardShortcuts();
    initSearchOperators();
});

// Export for external use
export {
    toggleSection,
    toggleSortDirection,
    savePreferences,
    loadPreferences,
    initKeyboardShortcuts,
    parseSearchOperators,
    initSearchOperators,
};
