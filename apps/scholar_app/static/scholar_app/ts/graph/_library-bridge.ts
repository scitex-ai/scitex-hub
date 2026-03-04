/**
 * Library Bridge - Save citation graph nodes to user's personal library
 */

import type { NetworkNode } from "./types";

/**
 * Save a graph node (paper) to the user's personal library.
 * Updates the button state to reflect save progress.
 */
export async function saveNodeToLibrary(node: NetworkNode): Promise<boolean> {
  const btn = document.querySelector(
    `.btn-save-to-library[data-doi="${node.id}"]`,
  ) as HTMLButtonElement;
  if (!btn) return false;

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

  try {
    const csrfToken =
      document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
        ?.value ||
      document.cookie
        .split("; ")
        .find((c) => c.startsWith("csrftoken="))
        ?.split("=")[1] ||
      "";

    const response = await fetch("/scholar/api/library/papers/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        title: node.title,
        authors: node.authors.join(", "),
        year: node.year,
        doi: node.id,
        source: "citation_graph",
      }),
    });

    if (response.ok) {
      btn.innerHTML = '<i class="fas fa-check"></i> Saved';
      btn.classList.add("saved");
      return true;
    } else {
      const data = await response.tson();
      btn.innerHTML = '<i class="fas fa-bookmark"></i> Save to Library';
      btn.disabled = false;
      console.error(
        "[CitationGraph] Save failed:",
        data.error || "Unknown error",
      );
      return false;
    }
  } catch (err) {
    btn.innerHTML = '<i class="fas fa-bookmark"></i> Save to Library';
    btn.disabled = false;
    console.error("[CitationGraph] Save error:", err);
    return false;
  }
}
