/**
 * Code Workspace File Tree Builder
 * Custom tree builder that keeps all folders collapsed by default
 * Includes file type icons for better visual identification
 */


interface TreeItem {
  name: string;
  path: string;
  type: 'file' | 'directory';
  is_symlink?: boolean;
  symlink_target?: string;
  children?: TreeItem[];
  git_status?: {
    status: string;  // M, A, D, ??
    staged: boolean;
  };
}

/**
 * Get git status indicator with appropriate color
 */
function getGitStatusIndicator(gitStatus: { status: string; staged: boolean } | undefined): string {
  if (!gitStatus) return '';

  const statusColors: { [key: string]: string } = {
    'M': '#e2c08d',   // Modified - orange/yellow
    'A': '#73c991',   // Added - green
    'D': '#f14c4c',   // Deleted - red
    '??': '#73c991',  // Untracked - green (like added)
    'R': '#73c991',   // Renamed - green
    'C': '#89d185',   // Copied - green
  };

  const statusLabels: { [key: string]: string } = {
    'M': 'M',
    'A': 'A',
    'D': 'D',
    '??': 'U',  // U for untracked
    'R': 'R',
    'C': 'C',
  };

  const color = statusColors[gitStatus.status] || '#858585';
  const label = statusLabels[gitStatus.status] || gitStatus.status;

  return `<span class="git-status-badge" style="color: ${color}; font-weight: 600; font-size: 11px; margin-left: 6px;" title="${gitStatus.staged ? 'Staged' : 'Modified'}">${label}</span>`;
}

/**
 * Get file icon based on extension (VS Code style)
 */
function getFileIcon(fileName: string): string {
  const ext = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
  const name = fileName.toLowerCase();

  // Comprehensive icon map (Gitea-inspired)
  const iconMap: { [key: string]: { icon: string, color: string } } = {
    // Programming languages
    '.py': { icon: 'fab fa-python', color: '#3776ab' },
    '.js': { icon: 'fab fa-js', color: '#f7df1e' },
    '.ts': { icon: 'fab fa-js', color: '#3178c6' },
    '.jsx': { icon: 'fab fa-react', color: '#61dafb' },
    '.tsx': { icon: 'fab fa-react', color: '#61dafb' },
    '.java': { icon: 'fab fa-java', color: '#007396' },
    '.go': { icon: 'fas fa-code', color: '#00add8' },
    '.rs': { icon: 'fas fa-gear', color: '#ce422b' },
    '.c': { icon: 'fas fa-file-code', color: '#555555' },
    '.cpp': { icon: 'fas fa-file-code', color: '#f34b7d' },

    // Web
    '.html': { icon: 'fab fa-html5', color: '#e34c26' },
    '.css': { icon: 'fab fa-css3-alt', color: '#264de4' },
    '.scss': { icon: 'fab fa-sass', color: '#cc6699' },

    // Data & Config
    '.json': { icon: 'fas fa-brackets-curly', color: '#ffa500' },
    '.yaml': { icon: 'fas fa-file-code', color: '#cb171e' },
    '.yml': { icon: 'fas fa-file-code', color: '#cb171e' },
    '.toml': { icon: 'fas fa-file-code', color: '#9c4121' },
    '.xml': { icon: 'fas fa-file-code', color: '#e37933' },
    '.csv': { icon: 'fas fa-table', color: '#217346' },

    // Documentation
    '.md': { icon: 'fab fa-markdown', color: '#000000' },
    '.txt': { icon: 'fas fa-file-alt', color: '#777777' },
    '.pdf': { icon: 'fas fa-file-pdf', color: '#ff0000' },

    // Scripts & Shell
    '.sh': { icon: 'fas fa-terminal', color: '#89e051' },
    '.bash': { icon: 'fas fa-terminal', color: '#89e051' },

    // Data Science
    '.r': { icon: 'fab fa-r-project', color: '#276dc3' },
    '.ipynb': { icon: 'fas fa-book', color: '#ff6f00' },
    '.sql': { icon: 'fas fa-database', color: '#e38c00' },

    // Images
    '.jpg': { icon: 'fas fa-image', color: '#00bfa5' },
    '.jpeg': { icon: 'fas fa-image', color: '#00bfa5' },
    '.png': { icon: 'fas fa-image', color: '#00bfa5' },
    '.gif': { icon: 'fas fa-image', color: '#00bfa5' },
    '.svg': { icon: 'fas fa-image', color: '#ffb300' },
    '.webp': { icon: 'fas fa-image', color: '#00bfa5' },

    // Archives
    '.zip': { icon: 'fas fa-file-archive', color: '#8b8b8b' },
    '.tar': { icon: 'fas fa-file-archive', color: '#8b8b8b' },
    '.gz': { icon: 'fas fa-file-archive', color: '#8b8b8b' },

    // Others
    '.tex': { icon: 'fas fa-file-alt', color: '#3d6117' },
    '.log': { icon: 'fas fa-file-lines', color: '#777777' },
    '.env': { icon: 'fas fa-cog', color: '#edb92e' },
  };

  // Special file names (like Gitea)
  const specialFiles: { [key: string]: { icon: string, color: string } } = {
    'readme.md': { icon: 'fas fa-book', color: '#00b0ff' },
    'readme': { icon: 'fas fa-book', color: '#00b0ff' },
    'license': { icon: 'fas fa-scroll', color: '#ffab00' },
    'dockerfile': { icon: 'fab fa-docker', color: '#2496ed' },
    'makefile': { icon: 'fas fa-cog', color: '#6d6d6d' },
    '.gitignore': { icon: 'fab fa-git-alt', color: '#f05032' },
    '.gitattributes': { icon: 'fab fa-git-alt', color: '#f05032' },
    'package.json': { icon: 'fab fa-npm', color: '#cb3837' },
    'tsconfig.json': { icon: 'fab fa-js', color: '#3178c6' },
    'requirements.txt': { icon: 'fab fa-python', color: '#3776ab' },
    'setup.py': { icon: 'fab fa-python', color: '#3776ab' },
  };

  if (specialFiles[name]) {
    const { icon, color } = specialFiles[name];
    return `<i class="${icon}" style="color: ${color}; width: 16px; text-align: center;"></i>`;
  }

  if (iconMap[ext]) {
    const { icon, color } = iconMap[ext];
    return `<i class="${icon}" style="color: ${color}; width: 16px; text-align: center;"></i>`;
  }

  // Default file icon
  return '<i class="fas fa-file" style="color: #777; width: 16px; text-align: center;"></i>';
}

/**
 * Builds HTML for file tree recursively (collapsed by default)
 * @param items - Array of tree items to render
 * @param username - Project owner username
 * @param slug - Project slug
 * @param level - Current nesting level (0 = root)
 * @returns HTML string for the tree
 */
export function buildCodeTreeHTML(items: TreeItem[], username: string, slug: string, level: number = 0): string {
  let html = "";
  // Add base padding for root level, then add indent for nested levels
  const basePadding = 12; // Base padding for root items
  const indent = basePadding + (level * 8);

  items.forEach((item) => {
    const itemPath = `/${username}/${slug}/${item.path}${item.type === "directory" ? "/" : ""}`;
    const itemId = `tree-${item.path.replace(/\//g, "-")}`;

    // Get appropriate icon
    let icon: string;
    if (item.type === "directory") {
      // Folder icon (yellow-ish like VS Code)
      icon = '<i class="fas fa-folder" style="color: #dcb67a; width: 16px; text-align: center;"></i>';
    } else {
      // File icon based on extension
      icon = getFileIcon(item.name);
    }

    const hasChildren = item.children && item.children.length > 0;

    if (item.type === "directory") {
      // FOLDER ROW - clickable to expand/collapse
      html += `<div class="file-tree-item file-tree-item--folder" style="padding-left: ${indent}px; display: flex; align-items: center;" onclick="toggleCodeFolder('${itemId}', event)">`;

      // FOLDER ICON BUTTON
      html += `<button type="button" class="folder-icon-button">`;

      // Chevron - ALWAYS collapsed by default
      if (hasChildren) {
        html += `<span class="file-tree-chevron">▸</span>`;
      } else {
        html += `<span class="file-tree-spacer"></span>`;
      }

      // Folder ICON
      html += `<span class="file-tree-icon">${icon}</span>`;
      html += `</button>`;

      // Folder NAME - just text, not a link (clicking the row toggles)
      html += `<span class="file-tree-folder-name" style="flex: 1;">${item.name}`;

      // Add symlink indicator if it's a symlink
      if (item.is_symlink && item.symlink_target) {
        html += `<span style="color: var(--color-fg-muted); margin-left: 4px; font-size: 12px;"> → ${item.symlink_target}</span>`;
      }

      // Add git status indicator for folders
      html += getGitStatusIndicator(item.git_status);

      html += `</span>`;

      // Folder ACTION BUTTONS (appear on hover)
      html += `<span class="folder-actions">`;
      html += `<button class="folder-action-btn" data-action="new-file" data-path="${item.path}" title="New file in ${item.name}" onclick="event.stopPropagation(); window.createFileInFolder('${item.path}')">`;
      html += `<i class="fas fa-file"></i><i class="fas fa-plus" style="font-size: 8px; margin-left: -4px; margin-top: -2px;"></i>`;
      html += `</button>`;
      html += `<button class="folder-action-btn" data-action="new-folder" data-path="${item.path}" title="New folder in ${item.name}" onclick="event.stopPropagation(); window.createFolderInFolder('${item.path}')">`;
      html += `<i class="fas fa-folder"></i><i class="fas fa-plus" style="font-size: 8px; margin-left: -4px; margin-top: -2px;"></i>`;
      html += `</button>`;
      html += `</span>`;

      html += `</div>`;

      // Children container - ALWAYS collapsed by default (never add 'expanded' class on initial render)
      if (hasChildren) {
        html += `<div id="${itemId}" class="file-tree-children" style="display: none;">`;
        html += buildCodeTreeHTML(item.children || [], username, slug, level + 1);
        html += `</div>`;
      }
    } else {
      // FILE - clickable, but handled by JavaScript (not navigation)
      html += `<div class="file-tree-item file-tree-item--file" style="padding-left: ${indent}px;">`;
      html += `<span class="file-tree-file" data-file-path="${item.path}" style="display: flex; align-items: center; gap: 8px; cursor: pointer;">`;
      html += `<span class="file-tree-spacer"></span>`;
      html += `<span class="file-tree-icon">${icon}</span>`;
      html += `<span class="file-tree-file-name">${item.name}`;

      // Add symlink indicator for files if it's a symlink
      if (item.is_symlink && item.symlink_target) {
        html += `<span style="color: var(--color-fg-muted); margin-left: 4px; font-size: 11px;"> → ${item.symlink_target}</span>`;
      }

      // Add git status indicator for files
      html += getGitStatusIndicator(item.git_status);

      html += `</span>`;
      html += `</span>`;
      html += `</div>`;
    }
  });

  return html;
}

/**
 * Toggles folder expand/collapse state for code workspace
 * @param folderId - ID of the folder container to toggle
 * @param event - Optional event to prevent propagation
 */
export function toggleCodeFolder(folderId: string, event?: Event): void {
  const folder = document.getElementById(folderId) as HTMLElement;
  if (!folder) return;

  // Find the chevron - it's in the previous sibling (the folder card div)
  const folderCard = folder.previousElementSibling;
  const chevron = folderCard?.querySelector(".file-tree-chevron") as HTMLElement;

  // Toggle visibility
  if (folder.style.display === "none") {
    // Expand
    folder.style.display = "block";
    folder.classList.add("expanded");
    if (chevron) {
      chevron.classList.add("expanded");
    }
  } else {
    // Collapse
    folder.style.display = "none";
    folder.classList.remove("expanded");
    if (chevron) {
      chevron.classList.remove("expanded");
    }
  }

  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
}
