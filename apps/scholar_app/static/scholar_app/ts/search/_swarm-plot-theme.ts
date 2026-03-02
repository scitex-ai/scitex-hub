/**
 * Theme color utilities for Swarm Plot Visualization
 *
 * Provides theme-aware color palettes for SciTeX swarm plots,
 * consistent with the workspace color scheme.
 */

/**
 * Theme color set for swarm plots
 */
export interface SwarmThemeColors {
  bg: string;
  text: string;
  grid: string;
  pointIncluded: string; // Bright - in filter range
  pointFiltered: string; // Dim/gray - outside filter range
  pointSelected: string; // Highlight - checkbox selected
  sizeIncluded: number;
  sizeFiltered: number;
}

/**
 * Get theme-aware colors for plots with distinct visual states.
 * Uses SciTeX workspace color palette for consistency.
 */
export function getThemeColors(): SwarmThemeColors {
  const isDark =
    document.documentElement.getAttribute("data-theme") === "dark" ||
    document.body.getAttribute("data-theme") === "dark" ||
    !document.documentElement.getAttribute("data-theme"); // Default to dark

  if (isDark) {
    return {
      bg: "rgba(13, 13, 13, 0)", // Transparent to show container bg
      text: "#6c8ba0", // scitex-color-04
      grid: "#3a3a3a",
      pointIncluded: "#6c8ba0", // scitex-color-04 - visible/included
      pointFiltered: "#374151", // Dark gray - filtered out
      pointSelected: "#8fa4b0", // scitex-color-05 - selected (brighter)
      sizeIncluded: 7,
      sizeFiltered: 4,
    };
  } else {
    return {
      bg: "rgba(243, 244, 246, 0)", // Transparent
      text: "#374151",
      grid: "#d1d5db",
      pointIncluded: "#506b7a", // scitex-color-03 - visible/included
      pointFiltered: "#d1d5db", // Light gray - filtered out
      pointSelected: "#6c8ba0", // scitex-color-04 - selected
      sizeIncluded: 7,
      sizeFiltered: 4,
    };
  }
}
