/**
 * API Response type definitions
 * Covers: PltzBundle, FigzBundle list responses and layout options
 */

import type { PltzCategory } from "./pltz-types";
import type { FigzLayout, LayoutConfig } from "./figz-types";

// =============================================================================
// API Response Types
// =============================================================================

export interface PltzBundleListResponse {
  bundles: PltzBundleSummary[];
}

export interface PltzBundleSummary {
  id: string;
  name: string;
  slug: string;
  category: PltzCategory;
  description: string;
  tags: string[];
  preview_url: string;
  created_at: string;
  updated_at: string;
}

export interface FigzBundleListResponse {
  bundles: FigzBundleSummary[];
}

export interface FigzBundleSummary {
  id: string;
  name: string;
  slug: string;
  layout: FigzLayout;
  panel_count: number;
  width_mm: number;
  height_mm?: number;
  description: string;
  preview_url: string;
  created_at: string;
  updated_at: string;
}

export interface LayoutOptionsResponse {
  layouts: Record<FigzLayout, LayoutConfig>;
}
