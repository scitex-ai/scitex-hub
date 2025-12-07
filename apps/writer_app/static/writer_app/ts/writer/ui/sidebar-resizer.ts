/**
 * Sidebar Resizer Module
 * Handles the resizable sidebar functionality
 *
 * Supports:
 * 1. Dragging the dedicated resizer handle
 * 2. Ctrl+drag anywhere in the file tree area
 * 3. Toggle collapse/expand via button
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/writer/ui/sidebar-resizer.ts loaded"
);

const STORAGE_KEY = "scitex-writer-sidebar-width";
const COLLAPSE_KEY = "scitex-writer-sidebar-collapsed";
const MIN_WIDTH = 40;  // Collapsed state width
const MAX_WIDTH = 600;
const DEFAULT_WIDTH = 280;
const COLLAPSED_WIDTH = 40;

// Module-level state for resize operations
let isResizing = false;
let startX = 0;
let startWidth = 0;
let sidebarElement: HTMLElement | null = null;

/**
 * Start resize operation
 * Auto-expands if sidebar is collapsed
 */
const startResize = (e: MouseEvent, sidebar: HTMLElement): void => {
  // Auto-expand if collapsed
  if (sidebar.classList.contains('collapsed')) {
    expandSidebar(sidebar);
  }

  isResizing = true;
  sidebarElement = sidebar;
  startX = e.clientX;
  startWidth = sidebar.getBoundingClientRect().width;
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
  e.preventDefault();
};

/**
 * Expand sidebar and sync toggle icon
 */
const expandSidebar = (sidebar: HTMLElement): void => {
  sidebar.classList.remove('collapsed');

  // Restore saved width
  const savedWidth = localStorage.getItem(STORAGE_KEY);
  if (savedWidth) {
    const width = parseInt(savedWidth, 10);
    if (width > COLLAPSED_WIDTH && width <= MAX_WIDTH) {
      sidebar.style.width = `${width}px`;
      sidebar.style.flexShrink = '0';
      sidebar.style.flexGrow = '0';
    } else {
      sidebar.style.width = `${DEFAULT_WIDTH}px`;
    }
  } else {
    sidebar.style.width = `${DEFAULT_WIDTH}px`;
  }

  // Update toggle icon
  updateToggleIcon(false);

  // Save collapse state
  localStorage.setItem(COLLAPSE_KEY, 'false');

  console.log("[SidebarResizer] Expanded sidebar");
};

/**
 * Collapse sidebar and sync toggle icon
 */
const collapseSidebar = (sidebar: HTMLElement): void => {
  sidebar.classList.add('collapsed');

  // Clear inline width so CSS takes over
  sidebar.style.width = '';
  sidebar.style.flexShrink = '';
  sidebar.style.flexGrow = '';

  // Update toggle icon
  updateToggleIcon(true);

  // Save collapse state
  localStorage.setItem(COLLAPSE_KEY, 'true');

  console.log("[SidebarResizer] Collapsed sidebar");
};

/**
 * Update toggle button icon based on collapse state
 */
const updateToggleIcon = (isCollapsed: boolean): void => {
  const toggleBtn = document.getElementById('sidebar-toggle');
  if (!toggleBtn) return;

  const icon = toggleBtn.querySelector('i');
  if (!icon) return;

  if (isCollapsed) {
    icon.classList.remove('fa-chevron-left');
    icon.classList.add('fa-chevron-right');
  } else {
    icon.classList.remove('fa-chevron-right');
    icon.classList.add('fa-chevron-left');
  }
};

/**
 * Handle mouse move during resize
 */
const handleMouseMove = (e: MouseEvent): void => {
  if (!isResizing || !sidebarElement) return;

  const delta = e.clientX - startX;
  const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, startWidth + delta));
  sidebarElement.style.width = `${newWidth}px`;
};

/**
 * End resize operation
 */
const handleMouseUp = (): void => {
  if (isResizing && sidebarElement) {
    isResizing = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";

    // Save width to localStorage
    const width = sidebarElement.getBoundingClientRect().width;
    localStorage.setItem(STORAGE_KEY, width.toString());
    console.log("[SidebarResizer] Saved width:", width);
    sidebarElement = null;
  }
};

/**
 * Initialize the sidebar resizer
 */
export const initSidebarResizer = (): void => {
  console.log("[SidebarResizer] Initializing...");
  const resizer = document.getElementById("sidebar-resizer");
  const sidebar = document.getElementById("writer-sidebar");
  const fileTree = document.getElementById("writer-file-tree");
  const toggleBtn = document.getElementById("sidebar-toggle");
  const collapsedHeader = sidebar?.querySelector(".sidebar-collapsed-header");

  console.log("[SidebarResizer] Elements found:", {
    resizer: !!resizer,
    sidebar: !!sidebar,
    fileTree: !!fileTree,
    toggleBtn: !!toggleBtn
  });

  if (!sidebar) {
    console.warn("[SidebarResizer] Sidebar not found, skipping initialization");
    return;
  }

  // Restore collapse state first
  const isCollapsed = localStorage.getItem(COLLAPSE_KEY) === 'true';
  if (isCollapsed) {
    sidebar.classList.add('collapsed');
    sidebar.style.width = '';
    sidebar.style.flexShrink = '';
    sidebar.style.flexGrow = '';
    updateToggleIcon(true);
    console.log("[SidebarResizer] Restored collapsed state");
  } else {
    // Restore saved width only if not collapsed
    const savedWidth = localStorage.getItem(STORAGE_KEY);
    if (savedWidth) {
      const width = parseInt(savedWidth, 10);
      if (width > COLLAPSED_WIDTH && width <= MAX_WIDTH) {
        sidebar.style.width = `${width}px`;
        sidebar.style.flexShrink = '0';
        sidebar.style.flexGrow = '0';
        console.log("[SidebarResizer] Restored width:", width);
      }
    }
  }

  // Method 1: Dedicated resizer handle
  if (resizer) {
    resizer.addEventListener("mousedown", (e: MouseEvent) => {
      startResize(e, sidebar);
    });
  }

  // Method 2: Ctrl+drag on file tree
  if (fileTree) {
    fileTree.addEventListener("mousedown", (e: MouseEvent) => {
      if (e.ctrlKey || e.metaKey) {
        console.log("[SidebarResizer] Ctrl+drag resize started");
        startResize(e, sidebar);
      }
    });

    // Change cursor when Ctrl is held over file tree
    fileTree.addEventListener("mousemove", (e: MouseEvent) => {
      if (!isResizing && (e.ctrlKey || e.metaKey)) {
        fileTree.style.cursor = "col-resize";
      } else if (!isResizing) {
        fileTree.style.cursor = "";
      }
    });

    fileTree.addEventListener("mouseleave", () => {
      if (!isResizing) {
        fileTree.style.cursor = "";
      }
    });
  }

  // Method 3: Toggle button (click to collapse/expand)
  if (toggleBtn) {
    toggleBtn.addEventListener("click", (e: MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (sidebar.classList.contains('collapsed')) {
        expandSidebar(sidebar);
      } else {
        collapseSidebar(sidebar);
      }
    });
  }

  // Method 4: Click on collapsed header to expand
  if (collapsedHeader) {
    collapsedHeader.addEventListener("click", (e: MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      expandSidebar(sidebar);
    });
  }

  // Global mouse move and up handlers
  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", handleMouseUp);
};

/**
 * Get current sidebar width
 */
export const getSidebarWidth = (): number => {
  const sidebar = document.getElementById("writer-sidebar");
  if (!sidebar) return DEFAULT_WIDTH;
  return sidebar.getBoundingClientRect().width;
};

/**
 * Set sidebar width programmatically
 */
export const setSidebarWidth = (width: number): void => {
  const sidebar = document.getElementById("writer-sidebar");
  if (!sidebar) return;

  const clampedWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, width));
  sidebar.style.width = `${clampedWidth}px`;
  localStorage.setItem(STORAGE_KEY, clampedWidth.toString());
};

// Auto-initialize when DOM is ready
// This ensures the resizer works even if initSidebarResizer() is not explicitly called
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSidebarResizer);
} else {
  // DOM already loaded, initialize immediately
  initSidebarResizer();
}
