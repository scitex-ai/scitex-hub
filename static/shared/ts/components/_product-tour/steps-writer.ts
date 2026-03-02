/**
 * Writer Page Tour Steps
 *
 * Provides guided walkthrough for new users:
 * - File structure explanation (which files to edit)
 * - LaTeX editing workflow
 * - Citations/Scholar integration
 * - Compilation process
 */
import { TourStep } from "./types";

export const WRITER_TOUR_STEPS: TourStep[] = [
  {
    selector: "#writer-sidebar",
    title: "Project Files",
    description:
      "Your manuscript structure: Edit 'manuscript.tex' for content. " +
      "References go in '.bib' files. Figures in 'figures/' folder.",
    position: "right",
  },
  {
    selector: "#file-tabs",
    title: "File Tabs",
    description:
      "Open multiple files simultaneously. Click tabs to switch. " +
      "manuscript.tex is your main document — start editing there.",
    position: "bottom",
  },
  {
    selector: ".latex-panel",
    title: "LaTeX Editor",
    description:
      "Write your manuscript here. Ctrl+S saves, Alt+Enter compiles. " +
      "Use \\cite{key} to add citations, \\ref{label} for cross-references.",
    position: "right",
  },
  {
    selector: ".preview-panel",
    title: "PDF Preview",
    description:
      "Live preview of your compiled PDF. Switch to Citations panel " +
      "to manage references from Scholar or upload BibTeX files.",
    position: "left",
  },
  {
    selector: ".selector-nav-item[onclick*='citations']",
    title: "Citations & Scholar",
    description:
      "Click here to access your references. Import from Scholar " +
      "or drag-and-drop .bib files. Click citation to insert \\cite{}.",
    position: "bottom",
  },
  {
    selector: ".compilation-status-indicators",
    title: "Compile & Preview",
    description:
      "Green = success, Yellow = warnings, Red = errors. " +
      "Click to view compilation logs and fix any LaTeX issues.",
    position: "bottom",
  },
  {
    selector: ".writer-details",
    title: "Document Info",
    description:
      "Track word counts per section, view metadata, and monitor " +
      "your progress. Collapse to maximize editing space.",
    position: "left",
  },
];
