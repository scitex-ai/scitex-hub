/**
 * GalleryTypes - Type definitions for GalleryCategories
 *
 * Extracted from GalleryCategories.ts for file-size compliance.
 */

export interface GalleryCategoryInfo {
  name: string;
  description: string;
  plots: string[];
}

export interface GalleryPlotInfo {
  name: string;
  display_name: string;
  png: string;
  svg?: string; // SVG URL for canvas insertion (element selection)
  json: string | null;
  csv: string | null;
}

export interface GalleryContents {
  success: boolean;
  exists: boolean;
  path: string;
  categories: Record<
    string,
    {
      name: string;
      plots: GalleryPlotInfo[];
      count: number;
    }
  >;
  total_plots: number;
}

export interface GalleryState {
  originalData: string[][] | null;
  currentData: string[][] | null;
  isModified: boolean;
  loadedFrom: {
    category: string;
    plotName: string;
  } | null;
}
