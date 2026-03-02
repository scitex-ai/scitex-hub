/**
 * Visualizer Page Tour Steps
 */
import { TourStep } from "./types";

export const VISUALIZER_TOUR_STEPS: TourStep[] = [
  {
    selector: ".vis-sidebar",
    title: "Project Files",
    description:
      "Browse your project files. Click on .pltz or data files to load them.",
    position: "right",
  },
  {
    selector: "#data-dropdown-container, .data-dropdown-container",
    title: "Table Selector",
    description: "Switch between data tables. Click + to create a new table.",
    position: "bottom",
  },
  {
    selector: "#data-table-container, .data-table-container",
    title: "Data Table",
    description:
      "View and edit your data. Import CSV/Excel or paste data directly.",
    position: "right",
  },
  {
    selector: "#figure-dropdown-container, .figure-dropdown-container",
    title: "Figure Selector",
    description: "Switch between figures. Click + to create a new canvas.",
    position: "bottom",
  },
  {
    selector: "#canvas-pane",
    title: "Canvas",
    description:
      "Your figure appears here. Drag objects, use alignment tools (Alt+A).",
    position: "left",
  },
  {
    selector: "#vis-properties, .vis-properties",
    title: "Details Panel",
    description:
      "Customize colors, labels, axes, and add statistical annotations.",
    position: "left",
  },
];
