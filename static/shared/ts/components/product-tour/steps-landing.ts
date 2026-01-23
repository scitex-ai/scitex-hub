/**
 * Landing Page Tour Steps
 */
import { TourStep } from "./types";

export const LANDING_TOUR_STEPS: TourStep[] = [
  {
    selector: ".header-project-selector-inline, .project-selector-btn",
    title: "Project Selector",
    description:
      "Switch between your research projects. All modules work within the selected project context.",
    position: "bottom",
  },
  {
    selector: '[data-shortcut="F"]',
    title: "Files",
    description:
      "Manage your research files and data. Browse, upload, and organize your project files.",
    position: "bottom",
  },
  {
    selector: '[data-shortcut="S"]',
    title: "Scholar",
    description:
      "Search and manage papers with abstracts for evidence-based AI assistance.",
    position: "bottom",
  },
  {
    selector: '[data-shortcut="C"]',
    title: "Console",
    description: "Run code in your own Apptainer container environment.",
    position: "bottom",
  },
  {
    selector: '[data-shortcut="V"]',
    title: "Visualizer",
    description:
      "Create reproducible figures as structured data. Edit and refine even after publication.",
    position: "bottom",
  },
  {
    selector: '[data-shortcut="W"]',
    title: "Writer",
    description:
      "Write manuscripts and revision letters with LaTeX. Real-time preview and citation integration.",
    position: "bottom",
  },
  {
    selector: '[href="/tools/"]',
    title: "Tools",
    description:
      "Access research utilities: bookmarklets, converters, and more.",
    position: "bottom",
  },
];
