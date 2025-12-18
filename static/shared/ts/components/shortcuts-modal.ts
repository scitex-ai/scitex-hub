/**
 * Keyboard Shortcuts Modal Component
 * Shows context-aware keyboard shortcuts help with sleek vis-style layout
 */

console.log("[DEBUG] shortcuts-modal.ts loaded");

/**
 * App context types
 */
type AppContext = 'global' | 'files' | 'scholar' | 'code' | 'vis' | 'writer';

/**
 * Shortcut definition
 */
interface ShortcutDef {
  keys: string;
  description: string;
}

/**
 * Section definition
 */
interface ShortcutSection {
  title: string;
  shortcuts: ShortcutDef[];
}

/**
 * Context-specific shortcut sections
 */
const CONTEXT_SECTIONS: Record<AppContext, ShortcutSection[]> = {
  global: [
    {
      title: 'Global Navigation',
      shortcuts: [
        { keys: 'Alt+F', description: 'Files' },
        { keys: 'Alt+S', description: 'Scholar' },
        { keys: 'Alt+C', description: 'Code' },
        { keys: 'Alt+V', description: 'Vis' },
        { keys: 'Alt+W', description: 'Writer' },
        { keys: 'Alt+Z', description: 'Zen Mode' },
      ],
    },
  ],
  files: [
    {
      title: 'Navigation',
      shortcuts: [
        { keys: 'Enter', description: 'Open item' },
        { keys: 'Backspace', description: 'Parent folder' },
        { keys: '/', description: 'Focus search' },
      ],
    },
    {
      title: 'File Actions',
      shortcuts: [
        { keys: 'Ctrl+N', description: 'New file' },
        { keys: 'Ctrl+Shift+N', description: 'New folder' },
        { keys: 'F2', description: 'Rename' },
        { keys: 'Del', description: 'Delete' },
      ],
    },
  ],
  scholar: [
    {
      title: 'Search',
      shortcuts: [
        { keys: 'Ctrl+F', description: 'Focus search' },
        { keys: 'Enter', description: 'Search' },
      ],
    },
    {
      title: 'Citations',
      shortcuts: [
        { keys: 'Ctrl+S', description: 'Save to library' },
        { keys: 'Ctrl+C', description: 'Copy citation' },
      ],
    },
  ],
  code: [
    {
      title: 'Files',
      shortcuts: [
        { keys: 'Ctrl+S', description: 'Save file' },
        { keys: 'Ctrl+N', description: 'New file' },
        { keys: 'Ctrl+Tab', description: 'Next tab' },
        { keys: 'Ctrl+Shift+Tab', description: 'Prev tab' },
      ],
    },
    {
      title: 'Terminal',
      shortcuts: [
        { keys: 'Ctrl+Shift+T', description: 'New terminal' },
        { keys: 'Ctrl+`', description: 'Toggle terminal' },
      ],
    },
    {
      title: 'View',
      shortcuts: [
        { keys: 'Ctrl+B', description: 'Toggle sidebar' },
      ],
    },
  ],
  vis: [
    {
      title: 'Basic',
      shortcuts: [
        { keys: 'Ctrl+C', description: 'Copy object' },
        { keys: 'Ctrl+V', description: 'Paste object' },
        { keys: 'Ctrl+D', description: 'Duplicate' },
        { keys: 'Ctrl+Z', description: 'Undo' },
        { keys: 'Ctrl+Y', description: 'Redo' },
        { keys: 'Del', description: 'Delete selected' },
        { keys: 'Arrow', description: 'Move 1px' },
        { keys: 'Shift+Arrow', description: 'Move 10px' },
      ],
    },
    {
      title: 'Align (Alt+A → ...)',
      shortcuts: [
        { keys: 'L', description: 'Left' },
        { keys: 'R', description: 'Right' },
        { keys: 'T', description: 'Top' },
        { keys: 'B', description: 'Bottom' },
        { keys: 'H', description: 'Distribute H (equal)' },
        { keys: 'V', description: 'Distribute V (equal)' },
        { keys: 'C', description: 'Center horizontal' },
        { keys: 'M', description: 'Center vertical' },
      ],
    },
    {
      title: 'Align by Axis (Alt+Shift+A → ...)',
      shortcuts: [
        { keys: 'L', description: 'Y-Axis (Left edge)' },
        { keys: 'R', description: 'Right edge' },
        { keys: 'T', description: 'Top edge' },
        { keys: 'B', description: 'X-Axis (Bottom edge)' },
        { keys: 'C', description: 'Horizontal center' },
        { keys: 'M', description: 'Vertical center' },
        { keys: 'S', description: 'Stack vertically' },
      ],
    },
    {
      title: 'Size (Alt+Z → ...)',
      shortcuts: [
        { keys: 'S', description: 'Match Size' },
        { keys: 'W', description: 'Match Width' },
        { keys: 'T', description: 'Match Height (Tall)' },
        { keys: 'C', description: 'Multiple Crop' },
      ],
    },
    {
      title: 'Arrange',
      shortcuts: [
        { keys: 'Alt+F', description: 'Bring to Front' },
        { keys: 'Alt+B', description: 'Send to Back' },
      ],
    },
    {
      title: 'View',
      shortcuts: [
        { keys: '+', description: 'Zoom in' },
        { keys: '-', description: 'Zoom out' },
        { keys: '0', description: 'Fit to window' },
        { keys: 'G', description: 'Toggle grid' },
        { keys: 'Alt+T', description: 'Toggle theme' },
      ],
    },
    {
      title: 'Group',
      shortcuts: [
        { keys: 'Ctrl+G', description: 'Group' },
        { keys: 'Ctrl+Shift+G', description: 'Ungroup' },
      ],
    },
  ],
  writer: [
    {
      title: 'Document',
      shortcuts: [
        { keys: 'Ctrl+S', description: 'Save' },
        { keys: 'Ctrl+B', description: 'Bold' },
        { keys: 'Ctrl+I', description: 'Italic' },
        { keys: 'Ctrl+K', description: 'Insert link' },
      ],
    },
    {
      title: 'Insert',
      shortcuts: [
        { keys: 'Ctrl+Shift+C', description: 'Citation' },
        { keys: 'Ctrl+Shift+E', description: 'Equation' },
        { keys: 'Ctrl+Shift+F', description: 'Figure' },
      ],
    },
  ],
};

/**
 * Detect current app context from URL path
 */
function detectContext(): AppContext {
  const path = window.location.pathname;
  if (path.startsWith('/files/')) return 'files';
  if (path.startsWith('/scholar/')) return 'scholar';
  if (path.startsWith('/code/')) return 'code';
  if (path.startsWith('/vis/')) return 'vis';
  if (path.startsWith('/writer/')) return 'writer';
  return 'global';
}

/**
 * Get display name for context
 */
function getContextName(context: AppContext): string {
  const names: Record<AppContext, string> = {
    global: 'Global',
    files: 'Files',
    scholar: 'Scholar',
    code: 'Code',
    vis: 'Vis',
    writer: 'Writer',
  };
  return names[context];
}

/**
 * Generate shortcuts HTML for sections
 */
function generateSectionsHTML(sections: ShortcutSection[]): string {
  return sections.map(section => `
    <div class="shortcuts-section">
      <h4>${section.title}</h4>
      ${section.shortcuts.map(s => `
        <div class="shortcut-row"><kbd>${s.keys}</kbd> ${s.description}</div>
      `).join('')}
    </div>
  `).join('');
}

/**
 * Show the keyboard shortcuts modal
 */
export function showShortcutsModal(): void {
  // Remove existing modal
  const existing = document.getElementById('shortcuts-modal-global');
  if (existing) {
    existing.remove();
    return; // Toggle behavior
  }

  const context = detectContext();
  const contextName = getContextName(context);

  // Build sections - always include global, then context-specific
  const allSections: ShortcutSection[] = [...CONTEXT_SECTIONS.global];
  if (context !== 'global') {
    allSections.push(...CONTEXT_SECTIONS[context]);
  }

  // Create modal
  const modal = document.createElement('div');
  modal.id = 'shortcuts-modal-global';
  modal.innerHTML = `
    <div class="shortcuts-modal-content">
      <div class="shortcuts-modal-header">
        <h3><i class="fas fa-keyboard"></i> Keyboard Shortcuts</h3>
        <span class="shortcuts-context-badge">${contextName}</span>
        <button class="shortcuts-modal-close">&times;</button>
      </div>
      <div class="shortcuts-modal-body">
        ${generateSectionsHTML(allSections)}
      </div>
      <div class="shortcuts-modal-footer">
        <a href="/keyboard-shortcuts/" class="shortcuts-full-page-link">
          View all shortcuts <i class="fas fa-external-link-alt"></i>
        </a>
      </div>
    </div>
  `;

  // Inject styles if not present
  injectStyles();

  // Apply modal overlay style
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    opacity: 0;
    transition: opacity 0.2s ease;
  `;

  // Add to page
  document.body.appendChild(modal);

  // Animate in
  requestAnimationFrame(() => {
    modal.style.opacity = '1';
  });

  // Close handlers
  const closeModal = () => {
    modal.style.opacity = '0';
    setTimeout(() => modal.remove(), 200);
  };

  modal.querySelector('.shortcuts-modal-close')?.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  // Escape key closes
  const escHandler = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      closeModal();
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);
}

/**
 * Toggle shortcuts modal
 */
export function toggleShortcutsModal(): void {
  const existing = document.getElementById('shortcuts-modal-global');
  if (existing) {
    existing.style.opacity = '0';
    setTimeout(() => existing.remove(), 200);
  } else {
    showShortcutsModal();
  }
}

/**
 * Styles are loaded from centralized shortcuts-modal.css
 * This function is kept for backwards compatibility but does nothing
 */
function injectStyles(): void {
  // Styles are now centralized in static/shared/css/components/shortcuts-modal.css
  // No need to inject inline styles
}

// Make available globally
declare global {
  interface Window {
    showShortcutsModal: typeof showShortcutsModal;
    toggleShortcutsModal: typeof toggleShortcutsModal;
  }
}

window.showShortcutsModal = showShortcutsModal;
window.toggleShortcutsModal = toggleShortcutsModal;
