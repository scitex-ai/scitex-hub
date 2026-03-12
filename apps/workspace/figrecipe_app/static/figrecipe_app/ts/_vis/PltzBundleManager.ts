/**
 * PltzBundleManager - Manages .pltz bundle operations
 *
 * Handles:
 * - CRUD operations for pltz bundles via REST API
 * - Bundle preview and data loading
 * - Geometry and hitmap retrieval
 * - Integration with gallery and canvas
 */

import type {
  PltzBundle,
  PltzBundleSummary,
  PltzBundleListResponse,
  PltzSpec,
  PltzStyle,
  PltzGeometry,
  PltzCategory,
} from "./types";

// API endpoints
const API_BASE = "/apps/vis/api/bundles/pltz";

export interface CreatePltzBundleParams {
  name: string;
  spec: PltzSpec;
  style: PltzStyle;
  data_csv?: string;
  category?: PltzCategory;
  description?: string;
  tags?: string[];
}

export interface UpdatePltzBundleParams {
  name?: string;
  spec?: PltzSpec;
  style?: PltzStyle;
  description?: string;
  tags?: string[];
  category?: PltzCategory;
}

export class PltzBundleManager {
  private bundles: Map<string, PltzBundle> = new Map();
  private listeners: Set<(bundles: PltzBundleSummary[]) => void> = new Set();
  private csrfToken: string;

  constructor() {
    this.csrfToken = this.getCSRFToken();
  }

  private getCSRFToken(): string {
    const cookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
  }

  private async fetchAPI<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.csrfToken,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `API error: ${response.status}`);
    }

    // Handle non-JSON responses (images, CSV)
    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      return response.json();
    }
    return response as unknown as T;
  }

  /**
   * List all pltz bundles for current user
   */
  async listBundles(params?: {
    category?: PltzCategory;
    search?: string;
  }): Promise<PltzBundleSummary[]> {
    const queryParams = new URLSearchParams();
    if (params?.category) queryParams.set("category", params.category);
    if (params?.search) queryParams.set("search", params.search);

    const query = queryParams.toString();
    const endpoint = query ? `/?${query}` : "/";

    const response = await this.fetchAPI<PltzBundleListResponse>(endpoint);
    this.notifyListeners(response.bundles);
    return response.bundles;
  }

  /**
   * Get full bundle details including spec, style, and geometry
   */
  async getBundle(bundleId: string): Promise<PltzBundle> {
    const bundle = await this.fetchAPI<PltzBundle>(`/${bundleId}/`);
    this.bundles.set(bundleId, bundle);
    return bundle;
  }

  /**
   * Create a new pltz bundle
   */
  async createBundle(params: CreatePltzBundleParams): Promise<PltzBundle> {
    const response = await this.fetchAPI<PltzBundle>("/create/", {
      method: "POST",
      body: JSON.stringify(params),
    });
    return response;
  }

  /**
   * Update an existing bundle
   */
  async updateBundle(
    bundleId: string,
    params: UpdatePltzBundleParams,
  ): Promise<PltzBundle> {
    const response = await this.fetchAPI<PltzBundle>(`/${bundleId}/update/`, {
      method: "PUT",
      body: JSON.stringify(params),
    });
    return response;
  }

  /**
   * Delete a bundle
   */
  async deleteBundle(bundleId: string): Promise<void> {
    await this.fetchAPI(`/${bundleId}/delete/`, {
      method: "DELETE",
    });
    this.bundles.delete(bundleId);
  }

  /**
   * Get preview image URL
   */
  getPreviewUrl(
    bundleId: string,
    type: "png" | "hitmap" | "overview" = "png",
  ): string {
    return `${API_BASE}/${bundleId}/preview/?type=${type}`;
  }

  /**
   * Get preview image as base64 data URL
   */
  async getPreviewBase64(
    bundleId: string,
    type: "png" | "hitmap" | "overview" = "png",
  ): Promise<string> {
    const response = await fetch(this.getPreviewUrl(bundleId, type));
    if (!response.ok) throw new Error("Failed to load preview");

    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  /**
   * Get CSV data from bundle
   */
  async getData(bundleId: string): Promise<string> {
    const response = await fetch(`${API_BASE}/${bundleId}/data/`, {
      headers: { "X-CSRFToken": this.csrfToken },
    });
    if (!response.ok) throw new Error("Failed to load data");
    return response.text();
  }

  /**
   * Get geometry cache for element hit-testing
   */
  async getGeometry(bundleId: string): Promise<PltzGeometry | null> {
    try {
      return await this.fetchAPI<PltzGeometry>(`/${bundleId}/geometry/`);
    } catch {
      return null;
    }
  }

  /**
   * Subscribe to bundle list changes
   */
  subscribe(listener: (bundles: PltzBundleSummary[]) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(bundles: PltzBundleSummary[]): void {
    this.listeners.forEach((listener) => listener(bundles));
  }

  /**
   * Get cached bundle or fetch if not available
   */
  async getCachedBundle(bundleId: string): Promise<PltzBundle> {
    const cached = this.bundles.get(bundleId);
    if (cached) return cached;
    return this.getBundle(bundleId);
  }

  /**
   * Create bundle from current canvas/data state
   */
  async createFromCurrentState(params: {
    name: string;
    spec: Partial<PltzSpec>;
    style: Partial<PltzStyle>;
    csvData?: string;
  }): Promise<PltzBundle> {
    const fullSpec: PltzSpec = {
      plot_id: params.name.toLowerCase().replace(/\s+/g, "_"),
      data: {
        csv: "data.csv",
        format: "wide",
      },
      axes: params.spec.axes || [],
      traces: params.spec.traces || [],
      ...params.spec,
    };

    const fullStyle: PltzStyle = {
      theme: {
        mode: "light",
        colors: {
          background: "#ffffff",
          axes_bg: "#ffffff",
          text: "#000000",
          spine: "#000000",
          tick: "#000000",
        },
      },
      size: { width_mm: 80, height_mm: 60 },
      font: {
        family: "Arial",
        axis_label_pt: 10,
        tick_label_pt: 8,
        title_pt: 12,
        legend_pt: 8,
      },
      traces: [],
      legend: {
        visible: true,
        location: "best",
        frameon: true,
        ncols: 1,
      },
      grid: false,
      ...params.style,
    };

    return this.createBundle({
      name: params.name,
      spec: fullSpec,
      style: fullStyle,
      data_csv: params.csvData,
    });
  }
}

// Singleton instance
export const pltzBundleManager = new PltzBundleManager();
