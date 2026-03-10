/**
 * Landing Page Tour Steps
 * Order: Writer, Scholar, Visualizer, Console, Verifier, Hub, Tools, Explorer
 */
import { TourStep } from "./types";

export const LANDING_TOUR_STEPS: TourStep[] = [
  {
    selector: ".header-project-selector-inline, .project-selector-btn",
    title: "Project Selector",
    description:
      "Your current project context. We've prepared 'default-project' as a demo template so you can explore Writer, Scholar, Visualizer, Console, and other modules right away.",
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
    selector: '[data-shortcut="S"]',
    title: "Scholar",
    description:
      "Search and manage papers with abstracts for evidence-based AI assistance.",
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
    selector: '[data-shortcut="C"]',
    title: "Console (Experimental)",
    description:
      "Your own isolated Apptainer container. Customize and switch containers freely. See /server-status for current resource availability.",
    position: "bottom",
  },
  {
    selector: '[data-shortcut="R"]',
    title: "Verifier",
    description:
      "Verify reproducibility chains. Trace any claim back to source data with interactive DAG visualization.",
    position: "bottom",
  },
  {
    selector: '[data-shortcut="H"]',
    title: "Hub",
    description:
      "Central project hub for file management, overview, and cross-module navigation.",
    position: "bottom",
  },
  {
    selector: '[href="/apps/tools/"]',
    title: "Tools",
    description:
      "Access research utilities: bookmarklets, converters, and more.",
    position: "bottom",
  },
];
