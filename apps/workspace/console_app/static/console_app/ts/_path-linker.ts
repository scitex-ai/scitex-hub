/**
 * Path Linker for Terminal
 * Automatically detects file paths in terminal output and converts them to clickable links
 */


interface PathMatch {
  text: string;      // Full matched text: "Saved to: ./path/file.jpg"
  path: string;      // Extracted path: "./path/file.jpg"
  start: number;     // Start position in string
  end: number;       // End position in string
}

/**
 * Path detection patterns
 */
const PATH_PATTERNS: RegExp[] = [
  // "Saved to:", "Created:", "Written to:", etc. followed by path
  /(Saved to|Created|Written to|Output|Exported to|Generating|Generated):\s+(\.\.?\/[\w\-\.\/]+\.\w+)/gi,

  // Relative paths: ./file.ext or ../file.ext
  /(\.\.?\/[\w\-\.\/]+\.(png|jpg|jpeg|gif|webp|svg|pdf|csv|tsv|txt|py|js|ts|jsx|tsx|md|json|yaml|yml|html|css|sh|bash|r|tex|bib))/gi,

  // Absolute paths (less common but useful)
  /(\/([\w\-\.\/]+)\.(png|jpg|jpeg|gif|webp|svg|pdf|csv|tsv|txt|py|js|ts|jsx|tsx|md|json|yaml|yml|html|css|sh|bash|r|tex|bib))/gi,

  // Just filename in current directory (more conservative - only with known prefixes)
  /(Saved|Created|Output):\s+([\w\-]+\.(png|jpg|jpeg|gif|webp|svg|pdf|csv|tsv))/gi,
];

/**
 * Detect file paths in text
 */
export function detectPaths(text: string): PathMatch[] {
  const matches: PathMatch[] = [];
  const seen = new Set<string>(); // Avoid duplicates

  for (const pattern of PATH_PATTERNS) {
    // Reset regex state
    pattern.lastIndex = 0;

    let match: RegExpExecArray | null;
    while ((match = pattern.exec(text)) !== null) {
      // Extract path (usually in group 2, fallback to group 1)
      const path = match[2] || match[1];
      const fullMatch = match[0];
      const key = `${match.index}:${fullMatch}`;

      // Avoid duplicate matches at same position
      if (!seen.has(key) && path) {
        matches.push({
          text: fullMatch,
          path: cleanPath(path),
          start: match.index,
          end: match.index + fullMatch.length
        });
        seen.add(key);
      }
    }
  }

  // Sort by position and remove overlaps
  return removeOverlaps(matches.sort((a, b) => a.start - b.start));
}

/**
 * Remove overlapping matches (keep first one)
 */
function removeOverlaps(matches: PathMatch[]): PathMatch[] {
  const result: PathMatch[] = [];
  let lastEnd = -1;

  for (const match of matches) {
    if (match.start >= lastEnd) {
      result.push(match);
      lastEnd = match.end;
    }
  }

  return result;
}

/**
 * Clean up path (remove prefixes like "Saved to:")
 */
function cleanPath(path: string): string {
  return path
    .replace(/^(Saved to|Created|Written to|Output|Exported to|Generating|Generated):\s+/i, '')
    .trim();
}

/**
 * Get file type from path
 */
export function getFileType(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase();

  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext || '')) {
    return 'image';
  }
  if (['pdf'].includes(ext || '')) {
    return 'pdf';
  }
  if (['csv', 'tsv'].includes(ext || '')) {
    return 'data';
  }
  if (['py', 'js', 'ts', 'jsx', 'tsx', 'html', 'css', 'sh', 'bash'].includes(ext || '')) {
    return 'code';
  }
  if (['md', 'txt', 'yaml', 'yml', 'json'].includes(ext || '')) {
    return 'text';
  }
  if (['tex', 'bib'].includes(ext || '')) {
    return 'latex';
  }
  return 'file';
}

/**
 * Get icon for file type
 */
export function getFileIcon(type: string): string {
  const icons: Record<string, string> = {
    image: '🖼️',
    pdf: '📄',
    data: '📊',
    console: '💻',
    text: '📝',
    latex: '📚',
    file: '📁'
  };
  return icons[type] || '📁';
}

/**
 * Convert relative path to file viewer URL
 */
export function pathToFileViewerUrl(
  relativePath: string,
  username: string,
  projectSlug: string
): string {
  // Clean up path
  let cleanedPath = relativePath
    .replace(/^\.\//, '')   // Remove "./"
    .replace(/^\.\.\//, ''); // Remove "../" (may need smarter handling)

  // Build URL to file viewer
  return `/${username}/${projectSlug}/blob/${cleanedPath}`;
}

/**
 * Render text with clickable path links
 * Returns HTML string with path links
 */
export function renderWithPathLinks(
  text: string,
  username: string,
  projectSlug: string
): string {
  const paths = detectPaths(text);

  if (paths.length === 0) {
    return escapeHtml(text);
  }

  // Split text into parts: text + link + text + link + ...
  let html = '';
  let lastIndex = 0;

  paths.forEach((pathMatch) => {
    // Add text before this path
    if (pathMatch.start > lastIndex) {
      html += escapeHtml(text.substring(lastIndex, pathMatch.start));
    }

    // Add clickable link
    const fileType = getFileType(pathMatch.path);
    const icon = getFileIcon(fileType);
    const url = pathToFileViewerUrl(pathMatch.path, username, projectSlug);

    html += `<a href="${url}"
                class="terminal-path-link"
                data-path="${escapeHtml(pathMatch.path)}"
                data-type="${fileType}"
                title="Open ${escapeHtml(pathMatch.path)}"
                onclick="event.preventDefault(); window.location.href='${url}';">
                <span class="path-icon">${icon}</span><span class="path-text">${escapeHtml(pathMatch.text)}</span>
              </a>`;

    lastIndex = pathMatch.end;
  });

  // Add remaining text
  if (lastIndex < text.length) {
    html += escapeHtml(text.substring(lastIndex));
  }

  return html;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
