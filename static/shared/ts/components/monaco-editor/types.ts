/**
 * Shared Monaco Editor Types
 * Used across /code/, /writer/, and other pages
 */

export interface MonacoEditorConfig {
  containerId: string;
  language?: string;
  value?: string;
  readOnly?: boolean;
  minimap?: boolean;
  lineNumbers?: "on" | "off" | "relative";
  wordWrap?: "on" | "off" | "wordWrapColumn" | "bounded";
  fontSize?: number;
  tabSize?: number;
  storageKeyPrefix?: string; // For localStorage keys (e.g., "code", "writer")
}

export interface MonacoEditorInstance {
  editor: any;
  monaco: any;
}

export const LANGUAGE_MAP: { [key: string]: string } = {
  ".py": "python",
  ".js": "javascript",
  ".ts": "typescript",
  ".tsx": "typescript",
  ".jsx": "javascript",
  ".html": "html",
  ".htm": "html",
  ".css": "css",
  ".scss": "scss",
  ".less": "less",
  ".json": "json",
  ".md": "markdown",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".sh": "shell",
  ".bash": "shell",
  ".zsh": "shell",
  ".r": "r",
  ".R": "r",
  ".tex": "latex",
  ".bib": "bibtex",
  ".txt": "plaintext",
  ".xml": "xml",
  ".svg": "xml",
  ".sql": "sql",
  ".go": "go",
  ".rs": "rust",
  ".java": "java",
  ".c": "c",
  ".cpp": "cpp",
  ".h": "c",
  ".hpp": "cpp",
  ".rb": "ruby",
  ".php": "php",
  ".lua": "lua",
  ".pl": "perl",
  ".swift": "swift",
  ".kt": "kotlin",
  ".scala": "scala",
  ".dockerfile": "dockerfile",
  ".toml": "toml",
  ".ini": "ini",
  ".cfg": "ini",
  ".conf": "ini",
};
