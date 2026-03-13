/**
 * Page Detection & Tour Configuration
 */
import { PageTourConfig } from "./types";
import { LANDING_TOUR_STEPS } from "./steps-landing";
import { FILES_TOUR_STEPS } from "./steps-files";
import { SCHOLAR_TOUR_STEPS } from "./steps-scholar";
import { CONSOLE_TOUR_STEPS } from "./steps-console";
import { VISUALIZER_TOUR_STEPS } from "./steps-visualizer";
import { WRITER_TOUR_STEPS } from "./steps-writer";

export const STORAGE_KEYS = {
  landing: "scitex_tour_landing",
  files: "scitex_tour_files",
  scholar: "scitex_tour_scholar",
  console: "scitex_tour_console",
  vis: "scitex_tour_vis",
  writer: "scitex_tour_writer",
};

export function getPageConfig(): PageTourConfig | null {
  const path = window.location.pathname;

  if (path === "/") {
    return { steps: LANDING_TOUR_STEPS, storageKey: STORAGE_KEYS.landing };
  }
  if (
    path.includes("/browse/") ||
    document.body.dataset.trackModule === "files"
  ) {
    return { steps: FILES_TOUR_STEPS, storageKey: STORAGE_KEYS.files };
  }
  if (path.includes("/apps/scholar/")) {
    return { steps: SCHOLAR_TOUR_STEPS, storageKey: STORAGE_KEYS.scholar };
  }
  if (path.includes("/apps/console/") || path.includes("/apps/workspace/")) {
    return { steps: CONSOLE_TOUR_STEPS, storageKey: STORAGE_KEYS.console };
  }
  if (path.includes("/apps/figrecipe/")) {
    return { steps: VISUALIZER_TOUR_STEPS, storageKey: STORAGE_KEYS.vis };
  }
  if (path.includes("/apps/writer/")) {
    return { steps: WRITER_TOUR_STEPS, storageKey: STORAGE_KEYS.writer };
  }

  return null;
}

export function hasCompletedTour(storageKey: string): boolean {
  return localStorage.getItem(storageKey) === "true";
}

export function markTourComplete(storageKey: string): void {
  localStorage.setItem(storageKey, "true");
}

export function resetTour(page?: string): void {
  if (page && page in STORAGE_KEYS) {
    localStorage.removeItem(STORAGE_KEYS[page as keyof typeof STORAGE_KEYS]);
  } else {
    // Reset all tours
    Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
    // Legacy key
    localStorage.removeItem("scitex_product_tour_complete");
  }
}
