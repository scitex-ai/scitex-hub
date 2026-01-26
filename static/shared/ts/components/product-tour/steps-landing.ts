/**
 * Landing Page Tour Steps
 */
import { TourStep } from "./types";

export const LANDING_TOUR_STEPS: TourStep[] = [
  {
    selector: ".header-project-selector-inline, .project-selector-btn",
    title: "Project Selector",
    description:
      "Your current project context. We've prepared 'default-project' as a demo template so you can explore Scholar, Console, Visualizer, Writer, and other modules right away.",
    position: "bottom",
  },
  {
    selector: '[data-shortcut="F"]',
    title: "Files",
    description:
      "Git-based file management with GitHub-like collaboration. Browse, commit, and organize files with Issues and Pull Requests for team research.",
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
    title: "Console (Experimental)",
    description:
      "Your own isolated Apptainer container. Customize and switch containers freely. See /server-status for current resource availability.",
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
