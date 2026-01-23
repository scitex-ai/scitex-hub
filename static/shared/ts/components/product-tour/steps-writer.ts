/**
 * Writer Page Tour Steps
 */
import { TourStep } from "./types";

export const WRITER_TOUR_STEPS: TourStep[] = [
  {
    selector: "#writer-sidebar",
    title: "Project Files",
    description:
      "Navigate your manuscript files: .tex, .bib, images, and figures.",
    position: "right",
  },
  {
    selector: "#file-tabs",
    title: "File Tabs",
    description:
      "Open multiple files in tabs. Click to switch, + to create new files.",
    position: "bottom",
  },
  {
    selector: ".latex-panel",
    title: "LaTeX Editor",
    description:
      "Monaco editor with LaTeX highlighting. Ctrl+S to save, Alt+Enter to compile.",
    position: "right",
  },
  {
    selector: ".preview-panel",
    title: "PDF Preview",
    description:
      "Live PDF preview. Use view switcher to access Citations, Figures, Tables.",
    position: "left",
  },
  {
    selector: ".compilation-status-indicators",
    title: "Compilation Status",
    description:
      "Section preview and full manuscript compilation status. Click to view logs.",
    position: "bottom",
  },
  {
    selector: ".writer-details",
    title: "Details Panel",
    description:
      "View and edit metadata, word counts, and document properties.",
    position: "left",
  },
];
