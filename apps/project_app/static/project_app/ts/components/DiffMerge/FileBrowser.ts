/**
 * DiffMerge File Browser Handler
 */

import { DiffMergeConfig, Side } from "./types";
import { getCSRFToken } from "./utils";

export class FileBrowser {
  private config: DiffMergeConfig;
  private currentSide: Side | null = null;
  private onFileSelected: (content: string, side: Side, filename: string) => void;

  constructor(
    config: DiffMergeConfig,
    onFileSelected: (content: string, side: Side, filename: string) => void
  ) {
    this.config = config;
    this.onFileSelected = onFileSelected;
  }

  /**
   * Setup modal for file browser
   */
  public setupModal(): void {
    const modal = document.getElementById("file-browser-modal");
    const closeBtn = modal?.querySelector(".modal-close");

    closeBtn?.addEventListener("click", () => {
      this.close();
    });

    modal?.addEventListener("click", (e) => {
      if (e.target === modal) {
        this.close();
      }
    });
  }

  /**
   * Open file browser
   */
  public open(side: Side): void {
    this.currentSide = side;
    const modal = document.getElementById("file-browser-modal");
    if (modal) {
      modal.style.display = "flex";
      this.loadFileTree();
    }
  }

  /**
   * Close file browser
   */
  public close(): void {
    const modal = document.getElementById("file-browser-modal");
    if (modal) {
      modal.style.display = "none";
    }
    this.currentSide = null;
  }

  /**
   * Load file tree
   */
  private async loadFileTree(): Promise<void> {
    const tree = document.getElementById("file-browser-tree");
    if (!tree) return;

    tree.innerHTML = "<p>Loading files...</p>";

    try {
      const response = await fetch(`${this.config.apiBaseUrl}api/_file-tree/`, {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to load file tree");
      }

      const data = await response.json();
      this.renderFileTree(data, tree);
    } catch (error) {
      console.error("Error loading file tree:", error);
      tree.innerHTML = "<p>Error loading files</p>";
    }
  }

  /**
   * Render file tree
   */
  private renderFileTree(data: any, container: HTMLElement): void {
    container.innerHTML = "";

    const renderNode = (
      node: any,
      parent: HTMLElement,
      path: string = ""
    ): void => {
      const currentPath = path ? `${path}/${node.name}` : node.name;

      if (node.type === "file") {
        const item = document.createElement("div");
        item.className = "file-tree-item";
        item.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 13.25 16h-9.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h9.5a.25.25 0 0 0 .25-.25V6h-2.75A1.75 1.75 0 0 1 9 4.25V1.5Zm6.75.062V4.25c0 .138.112.25.25.25h2.688l-.011-.013-2.914-2.914-.013-.011Z"></path>
          </svg>
          <span>${node.name}</span>
        `;
        item.addEventListener("click", () => {
          this.selectFile(currentPath);
        });
        parent.appendChild(item);
      } else if (node.type === "directory" && node.children) {
        const dirContainer = document.createElement("div");
        dirContainer.style.marginLeft = "1rem";

        const dirHeader = document.createElement("div");
        dirHeader.className = "file-tree-item";
        dirHeader.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M.513 1.513A1.75 1.75 0 0 1 1.75 1h3.5c.55 0 1.07.26 1.4.7l.9 1.2a.25.25 0 0 0 .2.1H13a1 1 0 0 1 1 1v.5H2.75a.75.75 0 0 0 0 1.5h11.978a1 1 0 0 1 .994 1.117L15 13.25A1.75 1.75 0 0 1 13.25 15H1.75A1.75 1.75 0 0 1 0 13.25V2.75c0-.464.184-.91.513-1.237Z"></path>
          </svg>
          <strong>${node.name}</strong>
        `;
        parent.appendChild(dirHeader);
        parent.appendChild(dirContainer);

        node.children.forEach((child: any) => {
          renderNode(child, dirContainer, currentPath);
        });
      }
    };

    if (data.children) {
      data.children.forEach((child: any) => {
        renderNode(child, container);
      });
    }
  }

  /**
   * Select file from repository
   */
  private async selectFile(filePath: string): Promise<void> {
    if (!this.currentSide) return;

    try {
      const formData = new FormData();
      formData.append("file_path", filePath);

      const response = await fetch(
        `${this.config.apiBaseUrl}api/load-file-from-repo/`,
        {
          method: "POST",
          headers: {
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to load file");
      }

      const data = await response.json();
      this.onFileSelected(data.content, this.currentSide, data.filename);
      this.close();
    } catch (error) {
      console.error("Error loading file:", error);
      alert(`Error loading file: ${error}`);
    }
  }
}
