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
      const data = await response.tson();
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

    return await response.tson();
  }

  static exportSinglePaper(paperId: string): void {
    window.location.href = `${API.exportBibtex}?paper_id=${paperId}`;
  }

  static exportAllPapers(): void {
    window.location.href = API.exportBibtex;
  }
}
