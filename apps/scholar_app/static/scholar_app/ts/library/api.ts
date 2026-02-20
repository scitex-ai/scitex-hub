/**
 * API functions for Scholar Library
 */

import { API, LibraryPaper, UpdatePaperData } from "./types";

export class LibraryAPI {
  static getCsrfToken(): string {
    const token = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1];
    return token || "";
  }

  static async fetchPapers(): Promise<LibraryPaper[]> {
    try {
      const response = await fetch(API.papers, {
        credentials: "same-origin",
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch papers: ${response.statusText}`);
      }
      const data = await response.json();
      return data.papers || [];
    } catch (error) {
      console.error("Failed to fetch papers:", error);
      return [];
    }
  }

  static async updatePaper(
    paperId: string,
    data: UpdatePaperData,
  ): Promise<void> {
    const response = await fetch(API.updatePaper(paperId), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCsrfToken(),
      },
      credentials: "same-origin",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Failed to update paper: ${response.statusText}`);
    }
  }

  static async removePaper(paperId: string): Promise<void> {
    const response = await fetch(API.removePaper(paperId), {
      method: "POST",
      headers: {
        "X-CSRFToken": this.getCsrfToken(),
      },
      credentials: "same-origin",
    });

    if (!response.ok) {
      throw new Error(`Failed to remove paper: ${response.statusText}`);
    }
  }

  static async importBibtex(file: File): Promise<{ imported_count: number }> {
    const formData = new FormData();
    formData.append("bibtex_file", file);

    const response = await fetch(API.importBibtex, {
      method: "POST",
      headers: {
        "X-CSRFToken": this.getCsrfToken(),
      },
      credentials: "same-origin",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to import BibTeX: ${response.statusText}`);
    }

    return await response.json();
  }

  static exportSinglePaper(paperId: string): void {
    window.location.href = `${API.exportBibtex}?paper_id=${paperId}`;
  }

  static exportAllPapers(): void {
    window.location.href = API.exportBibtex;
  }

  static async fetchPaperBibtex(paperId: string): Promise<string> {
    const response = await fetch(API.paperBibtex(paperId), {
      credentials: "same-origin",
    });
    if (!response.ok) throw new Error("Failed to fetch BibTeX");
    const data = await response.json();
    return data.bibtex || "";
  }

  static exportNamedBib(paperIds: string[], query: string): void {
    const body = JSON.stringify({ paper_ids: paperIds, query });
    const form = document.createElement("form");
    form.method = "POST";
    form.action = API.exportNamedBib;
    const csrfInput = document.createElement("input");
    csrfInput.type = "hidden";
    csrfInput.name = "csrfmiddlewaretoken";
    csrfInput.value = this.getCsrfToken();
    form.appendChild(csrfInput);
    const bodyInput = document.createElement("input");
    bodyInput.type = "hidden";
    bodyInput.name = "__body";
    bodyInput.value = body;
    form.appendChild(bodyInput);
    // Use fetch for proper JSON POST download
    fetch(API.exportNamedBib, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCsrfToken(),
      },
      credentials: "same-origin",
      body,
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const filename =
          query
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "_")
            .slice(0, 50) + ".bib";
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      });
  }
}
