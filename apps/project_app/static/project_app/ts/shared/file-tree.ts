/**
 * Shared File Tree Module
 * Provides reusable file tree building and interaction functionality with colorful icons
 * Corresponds to: Used across multiple pages with file tree sidebars
 *
 * Auto-initializes if #project-data element exists with data-project-owner/slug attributes
 */

console.log(
  "[DEBUG] apps/project_app/static/project_app/ts/shared/file-tree.ts loaded",
);

// Declare window extensions for TypeScript
declare global {
  interface Window {
    toggleFolder: typeof toggleFolder;
    loadFileTree: typeof loadFileTree;
    toggleHiddenFiles: typeof toggleHiddenFiles;
  }
}

/** localStorage key for hidden files toggle state */
const HIDDEN_FILES_KEY = "scitex-show-hidden-files";

/** System noise files always hidden */
const SYSTEM_NOISE = [".DS_Store", "Thumbs.db"];

/** Check if a file/directory name is a dotfile (hidden) */
function isDotfile(name: string): boolean {
  return name.startsWith(".") && !SYSTEM_NOISE.includes(name);
}

/** Check if a file is system noise (always hidden) */
function isSystemNoise(name: string): boolean {
  return SYSTEM_NOISE.includes(name);
}

/** Get show-hidden-files preference from localStorage */
function getShowHidden(): boolean {
  return localStorage.getItem(HIDDEN_FILES_KEY) === "true";
}

/** Filter tree items based on hidden file preference */
function filterTreeItems(items: TreeItem[]): TreeItem[] {
  const showHidden = getShowHidden();

  return (
    items
      .filter((item) => {
        // Always hide system noise
        if (item.type === "file" && isSystemNoise(item.name)) {
          return false;
        }
        // Hide dotfiles unless toggle is on
        if (!showHidden && isDotfile(item.name)) {
          return false;
        }
        return true;
      })
      .map((item) => {
        if (item.type === "directory" && item.children) {
          return { ...item, children: filterTreeItems(item.children) };
        }
        return item;
      })
      // Remove empty directories after filtering (except when showing hidden)
      .filter((item) => {
        if (
          item.type === "directory" &&
          item.children &&
          item.children.length === 0
        ) {
          // Keep directories that were originally non-empty (children were filtered out)
          return false;
        }
        return true;
      })
  );
}

/** Toggle hidden files visibility and re-render the tree */
export function toggleHiddenFiles(): void {
  const current = getShowHidden();
  localStorage.setItem(HIDDEN_FILES_KEY, String(!current));
  updateToggleButton(!current);

  // Re-render the file tree
  const projectData = document.getElementById("project-data");
  if (projectData) {
    const owner = projectData.dataset.projectOwner;
    const slug = projectData.dataset.projectSlug;
    if (owner && slug) {
      loadFileTree(owner, slug, "file-tree");
    }
  }
}

/** Update the toggle button icon to reflect current state */
function updateToggleButton(showHidden: boolean): void {
  const btn = document.getElementById("hidden-files-toggle");
  if (!btn) return;
  const icon = btn.querySelector("i");
  if (!icon) return;

  if (showHidden) {
    icon.className = "fas fa-eye";
    btn.title = "Hide hidden files";
    btn.classList.add("active");
  } else {
    icon.className = "fas fa-eye-slash";
    btn.title = "Show hidden files";
    btn.classList.remove("active");
  }
}

export interface TreeItem {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: TreeItem[];
  is_symlink?: boolean;
  symlink_target?: string;
}

/**
 * Get colorful file icon based on extension (VS Code style)
 */
function getColorfulFileIcon(fileName: string): string {
  const ext = fileName.substring(fileName.lastIndexOf(".")).toLowerCase();
  const name = fileName.toLowerCase();

  // Comprehensive icon map (Gitea-inspired)
  const iconMap: { [key: string]: { icon: string; color: string } } = {
    // Programming languages
    ".py": { icon: "fab fa-python", color: "#3776ab" },
    ".js": { icon: "fab fa-js", color: "#f7df1e" },
    ".ts": { icon: "fab fa-js", color: "#3178c6" },
    ".jsx": { icon: "fab fa-react", color: "#61dafb" },
    ".tsx": { icon: "fab fa-react", color: "#61dafb" },
    ".java": { icon: "fab fa-java", color: "#007396" },
    ".go": { icon: "fas fa-code", color: "#00add8" },
    ".rs": { icon: "fas fa-gear", color: "#ce422b" },
    ".c": { icon: "fas fa-file-code", color: "#555555" },
    ".cpp": { icon: "fas fa-file-code", color: "#f34b7d" },

    // Web
    ".html": { icon: "fab fa-html5", color: "#e34c26" },
    ".css": { icon: "fab fa-css3-alt", color: "#264de4" },
    ".scss": { icon: "fab fa-sass", color: "#cc6699" },

    // Data & Config
    ".json": { icon: "fas fa-brackets-curly", color: "#ffa500" },
    ".yaml": { icon: "fas fa-file-code", color: "#cb171e" },
    ".yml": { icon: "fas fa-file-code", color: "#cb171e" },
    ".toml": { icon: "fas fa-file-code", color: "#9c4121" },
    ".xml": { icon: "fas fa-file-code", color: "#e37933" },
    ".csv": { icon: "fas fa-table", color: "#217346" },

    // Documentation
    ".md": { icon: "fab fa-markdown", color: "#000000" },
    ".txt": { icon: "fas fa-file-alt", color: "#777777" },
    ".pdf": { icon: "fas fa-file-pdf", color: "#ff0000" },

    // Scripts & Shell
    ".sh": { icon: "fas fa-terminal", color: "#89e051" },
    ".bash": { icon: "fas fa-terminal", color: "#89e051" },

    // Data Science
    ".r": { icon: "fab fa-r-project", color: "#276dc3" },
    ".ipynb": { icon: "fas fa-book", color: "#ff6f00" },
    ".sql": { icon: "fas fa-database", color: "#e38c00" },

    // Images
    ".jpg": { icon: "fas fa-image", color: "#00bfa5" },
    ".jpeg": { icon: "fas fa-image", color: "#00bfa5" },
    ".png": { icon: "fas fa-image", color: "#00bfa5" },
    ".gif": { icon: "fas fa-image", color: "#00bfa5" },
    ".svg": { icon: "fas fa-image", color: "#ffb300" },
    ".webp": { icon: "fas fa-image", color: "#00bfa5" },

    // Archives
    ".zip": { icon: "fas fa-file-archive", color: "#8b8b8b" },
    ".tar": { icon: "fas fa-file-archive", color: "#8b8b8b" },
    ".gz": { icon: "fas fa-file-archive", color: "#8b8b8b" },

    // Others
    ".tex": { icon: "fas fa-file-alt", color: "#3d6117" },
    ".log": { icon: "fas fa-file-lines", color: "#777777" },
    ".env": { icon: "fas fa-cog", color: "#edb92e" },
  };

  // Special file names (like Gitea)
  const specialFiles: { [key: string]: { icon: string; color: string } } = {
    "readme.md": { icon: "fas fa-book", color: "#00b0ff" },
    readme: { icon: "fas fa-book", color: "#00b0ff" },
    license: { icon: "fas fa-scroll", color: "#ffab00" },
    dockerfile: { icon: "fab fa-docker", color: "#2496ed" },
    makefile: { icon: "fas fa-cog", color: "#6d6d6d" },
    ".gitignore": { icon: "fab fa-git-alt", color: "#f05032" },
    ".gitattributes": { icon: "fab fa-git-alt", color: "#f05032" },
    "package.json": { icon: "fab fa-npm", color: "#cb3837" },
    "tsconfig.json": { icon: "fab fa-js", color: "#3178c6" },
    "requirements.txt": { icon: "fab fa-python", color: "#3776ab" },
    "setup.py": { icon: "fab fa-python", color: "#3776ab" },
  };

  if (specialFiles[name]) {
    const { icon, color } = specialFiles[name];
    return `<i class="${icon} file-tree-icon-colored" data-color="${color}"></i>`;
  }

  if (iconMap[ext]) {
    const { icon, color } = iconMap[ext];
    return `<i class="${icon} file-tree-icon-colored" data-color="${color}"></i>`;
  }

  // Default file icon
  return '<i class="fas fa-file file-tree-icon-colored file-tree-icon-default"></i>';
}

/** Inject dynamic color styles for file icons via <style> tag */
function injectIconColorStyles(): void {
  if (document.getElementById("file-tree-icon-styles")) return;
  const style = document.createElement("style");
  style.id = "file-tree-icon-styles";
  style.textContent = `
    .file-tree-icon-colored {
      width: 16px;
      text-align: center;
    }
    .file-tree-icon-default {
      color: #777;
    }
    .file-tree-icon-folder {
      color: #dcb67a;
    }
    .file-tree-error {
      color: var(--color-fg-muted);
      padding: 0.5rem;
    }
  `;
  document.head.appendChild(style);
}

/** Apply data-color attributes as inline color after DOM render */
function applyIconColors(): void {
  const icons = document.querySelectorAll<HTMLElement>(
    ".file-tree-icon-colored[data-color]",
  );
  icons.forEach((el) => {
    const color = el.getAttribute("data-color");
    if (color) el.style.color = color;
  });
}

/**
 * Checks if a tree item path is in the current URL path
 * @param itemPath - The path of the tree item
 * @param currentPath - The current URL path
 * @returns True if the item is in the current path
 */
function isInCurrentPath(itemPath: string, currentPath: string): boolean {
  // Normalize paths by removing trailing slashes and decoding URI components
  const normalizedItemPath = decodeURIComponent(itemPath.replace(/\/$/, ""));
  const normalizedCurrentPath = decodeURIComponent(
    currentPath.replace(/\/$/, ""),
  );

  // Check if current path starts with item path (for directories)
  return normalizedCurrentPath.includes(normalizedItemPath);
}

/**
 * Builds HTML for file tree recursively
 * @param items - Array of tree items to render
 * @param username - Project owner username
 * @param slug - Project slug
 * @param level - Current nesting level (0 = root)
 * @returns HTML string for the tree
 */
export function buildTreeHTML(
  items: TreeItem[],
  username: string,
  slug: string,
  level: number = 0,
): string {
  let html = "";
  // No inline padding - indentation handled by CSS .file-tree-children.expanded
  const currentPath = window.location.pathname;

  items.forEach((item: TreeItem) => {
    const itemPath = `/${username}/${slug}/${item.path}${item.type === "directory" ? "/" : ""}`;
    const isActive =
      item.type === "directory"
        ? currentPath.includes(`/${item.path}/`) ||
          currentPath.includes(`/${item.path}`)
        : currentPath.endsWith(`/blob/${item.path}`);

    // Determine if this folder should be auto-expanded (if it's in the current path)
    const shouldExpand = isInCurrentPath(item.path, currentPath);

    // Debug logging
    if (item.type === "directory" && level < 3) {
      console.log(
        `[FileTree] ${item.name}: path="${item.path}", currentPath="${currentPath}", shouldExpand=${shouldExpand}`,
      );
    }

    // Get colorful icons
    let icon: string;
    if (item.type === "directory") {
      // Folder icon (yellow-ish like VS Code)
      icon =
        '<i class="fas fa-folder file-tree-icon-colored file-tree-icon-folder"></i>';
    } else {
      // Colorful file icon based on extension
      icon = getColorfulFileIcon(item.name);
    }

    const hasChildren = item.children && item.children.length > 0;
    const itemId = `tree-${item.path.replace(/\//g, "-")}`;

    if (item.type === "directory") {
      // FOLDER ROW - entire div is clickable to expand/collapse (except the folder name)
      // No inline padding-left - CSS handles indentation via .file-tree-children nesting
      html += `<div class="file-tree-item file-tree-item--folder ${isActive ? "active" : ""}" onclick="toggleFolder('${itemId}', event)">`;

      // FOLDER ICON BUTTON - visual grouping of chevron and icon
      html += `<button type="button" class="folder-icon-button">`;

      // Chevron - part of the icon button
      if (hasChildren) {
        html += `<span class="file-tree-chevron ${shouldExpand ? "expanded" : ""}">▸</span>`;
      } else {
        html += `<span class="file-tree-spacer"></span>`;
      }

      // Folder ICON
      html += `<span class="file-tree-icon">${icon}</span>`;
      html += `</button>`;

      // Folder NAME - link that navigates (stops propagation to prevent toggle)
      html += `<a href="${itemPath}" class="file-tree-folder-link" onclick="event.stopPropagation()">${item.name}`;

      // Add symlink indicator if it's a symlink
      if (item.is_symlink && item.symlink_target) {
        html += `<span style="color: var(--color-fg-muted); margin-left: 4px; font-size: 12px;"> → ${item.symlink_target}</span>`;
      }

      html += `</a>`;

      html += `</div>`;

      // Children container
      if (hasChildren) {
        html += `<div id="${itemId}" class="file-tree-children ${shouldExpand ? "expanded" : ""}">`;
        html += buildTreeHTML(item.children || [], username, slug, level + 1);
        html += `</div>`;
      }
    } else {
      // FILE - just a link
      // No inline padding-left - CSS handles indentation via .file-tree-children nesting
      html += `<div class="file-tree-item file-tree-item--file ${isActive ? "active" : ""}">`;
      html += `<a href="/${username}/${slug}/blob/${item.path}" class="file-tree-file">`;
      html += `<span class="file-tree-spacer"></span>`;
      html += `<span class="file-tree-icon">${icon}</span><span class="file-tree-file-name">${item.name}`;

      // Add symlink indicator for files if it's a symlink
      if (item.is_symlink && item.symlink_target) {
        html += `<span style="color: var(--color-fg-muted); margin-left: 4px; font-size: 11px;"> → ${item.symlink_target}</span>`;
      }

      html += `</span>`;
      html += `</a>`;
      html += `</div>`;
    }
  });

  return html;
}

/**
 * Toggles folder expand/collapse state
 * @param folderId - ID of the folder container to toggle
 * @param event - Optional event to prevent propagation
 */
export function toggleFolder(folderId: string, event?: Event): void {
  const folder = document.getElementById(folderId);
  if (!folder) return;

  // Find the chevron - it's in the previous sibling (the folder card div)
  const folderCard = folder.previousElementSibling;
  const chevron = folderCard?.querySelector(
    ".file-tree-chevron",
  ) as HTMLElement;

  if (folder.classList.contains("expanded")) {
    folder.classList.remove("expanded");
    if (chevron) chevron.classList.remove("expanded");
  } else {
    folder.classList.add("expanded");
    if (chevron) chevron.classList.add("expanded");
  }

  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
}

/**
 * Loads file tree from API and renders it
 * @param username - Project owner username
 * @param slug - Project slug
 * @param containerId - ID of container element to render tree into
 */
export async function loadFileTree(
  username: string,
  slug: string,
  containerId: string = "file-tree",
): Promise<void> {
  try {
    const response = await fetch(`/${username}/${slug}/api/file-tree/`);
    const data = await response.json();

    const treeContainer = document.getElementById(containerId);
    if (!treeContainer) {
      console.error(`File tree container #${containerId} not found`);
      return;
    }

    if (data.success) {
      const filtered = filterTreeItems(data.tree);
      treeContainer.innerHTML = buildTreeHTML(filtered, username, slug);
      injectIconColorStyles();
      applyIconColors();
    } else {
      injectIconColorStyles();
      treeContainer.innerHTML =
        '<div class="file-tree-error">Error loading file tree</div>';
    }
  } catch (err) {
    console.error("Failed to load file tree:", err);
    const treeContainer = document.getElementById(containerId);
    if (treeContainer) {
      treeContainer.innerHTML =
        '<div class="file-tree-error">Error loading file tree</div>';
    }
  }
}

// Expose functions globally for onclick handlers
window.toggleFolder = toggleFolder;
window.loadFileTree = loadFileTree;
window.toggleHiddenFiles = toggleHiddenFiles;

// Auto-initialize if project-data element exists
document.addEventListener("DOMContentLoaded", () => {
  const projectData = document.getElementById("project-data");
  if (projectData) {
    const owner = projectData.dataset.projectOwner;
    const slug = projectData.dataset.projectSlug;
    if (owner && slug) {
      loadFileTree(owner, slug, "file-tree");
    }
  }

  // Wire up the hidden files toggle button
  const toggleBtn = document.getElementById("hidden-files-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleHiddenFiles();
    });
    // Set initial button state
    updateToggleButton(getShowHidden());
  }
});
