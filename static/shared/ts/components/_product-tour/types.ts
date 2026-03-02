/**
 * Product Tour Type Definitions
 */

export interface TourStep {
  selector: string;
  title: string;
  description: string;
  position?: "top" | "bottom" | "left" | "right";
}

export interface PageTourConfig {
  steps: TourStep[];
  storageKey: string;
}
