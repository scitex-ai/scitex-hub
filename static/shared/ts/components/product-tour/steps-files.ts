/**
 * Files Page Tour Steps
 */
import { TourStep } from "./types";

export const FILES_TOUR_STEPS: TourStep[] = [
  {
    selector: ".repo-header",
    title: "Project Header",
    description:
      "View project info, star/watch counts. Click breadcrumbs to navigate directories.",
    position: "bottom",
  },
  {
    selector: "#branch-dropdown-btn-header, .repo-branch-selector",
    title: "Branch Selector",
    description:
      "Switch between branches. Click to see all branches or create new ones.",
    position: "bottom",
  },
  {
    selector: "#goto-file-input",
    title: "Quick File Search",
    description:
      "Type to quickly find files by name. Press Enter to navigate to the file.",
    position: "bottom",
  },
  {
    selector: "#add-file-btn",
    title: "Add Files",
    description:
      "Create new files or upload existing ones. Drag and drop is also supported.",
    position: "bottom",
  },
  {
    selector: "#copy-project-btn",
    title: "Copy Project Content",
    description:
      "Copy all text files as concatenated content or download as a single file.",
    position: "bottom",
  },
  {
    selector: ".repo-action-buttons",
    title: "Project Actions",
    description:
      "Watch for notifications, star to bookmark, fork to create your own copy, or clone locally.",
    position: "bottom",
  },
  {
    selector: ".file-browser, .file-table",
    title: "File Browser",
    description:
      "Click files to view content. Click folders to navigate. Shows last commit info for each file.",
    position: "top",
  },
];
