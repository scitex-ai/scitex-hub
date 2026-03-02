/**
 * Console Page Tour Steps
 */
import { TourStep } from "./types";

export const CONSOLE_TOUR_STEPS: TourStep[] = [
  {
    selector: "#code-sidebar",
    title: "Project Files",
    description:
      "Browse and manage your project files. Click to open, right-click for more options.",
    position: "right",
  },
  {
    selector: ".code-toolbar",
    title: "Toolbar",
    description:
      "Save (Ctrl+S), Run (Ctrl+Enter), Commit changes. Delete files with trash icon.",
    position: "bottom",
  },
  {
    selector: "#file-tabs, .file-tabs",
    title: "File Tabs",
    description:
      "Open multiple files in tabs. Click tabs to switch, + to create new files.",
    position: "bottom",
  },
  {
    selector: "#monaco-editor, .code-editor-container",
    title: "Code Editor",
    description:
      "Monaco-powered editor with syntax highlighting. Supports Python, JS, and more.",
    position: "bottom",
  },
  {
    selector: "#code-terminal-panel, .code-terminal-panel",
    title: "Terminal & Jobs",
    description:
      "Integrated terminal with bash. Switch to Jobs tab to monitor background processes.",
    position: "left",
  },
];
