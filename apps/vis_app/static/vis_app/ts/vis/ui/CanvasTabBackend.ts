/**
 * Backend operations for canvas tabs
 * Handles communication with Django API
 */

import { getCSRFToken } from "./CanvasTabStorage";

/**
 * Create a figz bundle on the backend using scitex package
 */
export async function createFigzBundleOnBackend(
  figureName: string,
  onBundleCreated?: (figureName: string, figurePath: string) => void,
): Promise<string | null> {
  const projectOwner = (window as any).projectOwner;
  const projectSlug = (window as any).projectSlug;

  if (!projectOwner || !projectSlug) {
    console.warn(
      "[CanvasTabBackend] No project context - cannot create figz bundle",
    );
    return null;
  }

  try {
    const response = await fetch("/vis/api/bundles/figz/create-empty/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        project_owner: projectOwner,
        project_slug: projectSlug,
        figure_name: figureName,
        canvas_size: { width_mm: 170, height_mm: 120 },
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error("[CanvasTabBackend] Failed to create figz bundle:", error);
      return null;
    }

    const result = await response.json();
    console.log(
      "[CanvasTabBackend] Created figz bundle:",
      result.directory_path,
    );

    if (onBundleCreated && result.directory_path) {
      onBundleCreated(figureName, result.directory_path);
    }

    return result.directory_path;
  } catch (error) {
    console.error("[CanvasTabBackend] Error creating figz bundle:", error);
    return null;
  }
}
