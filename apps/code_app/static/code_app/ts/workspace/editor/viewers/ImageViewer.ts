/**
 * Image Viewer
 * Handles image file display with zoom and pan functionality
 */

export class ImageViewer {
  /**
   * Display an image file
   */
  display(
    wrapper: HTMLElement,
    filePath: string,
    blobUrl?: string,
    createToolbar?: (filePath: string, fileType: string) => HTMLElement
  ): void {
    wrapper.className = "media-viewer-image-wrapper";

    // Toolbar
    if (createToolbar) {
      const toolbar = createToolbar(filePath, "image");
      wrapper.appendChild(toolbar);
    }

    // Image container with zoom/pan support
    const imageContainer = document.createElement("div");
    imageContainer.className = "media-viewer-image-container";

    const img = document.createElement("img");
    img.className = "media-viewer-image";
    img.alt = filePath.split("/").pop() || "Image";

    // Use blob URL if available, otherwise construct API URL
    if (blobUrl) {
      img.src = blobUrl;
    } else {
      const projectData = document.getElementById("project-data");
      const projectId = projectData?.dataset.projectId || "";
      img.src = `/code/api/file-content/${filePath}?project_id=${projectId}&raw=true`;
    }

    img.onerror = () => {
      img.style.display = "none";
      const errorMsg = document.createElement("div");
      errorMsg.className = "media-viewer-error";
      errorMsg.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        <p>Failed to load image</p>
        <small>${filePath}</small>
      `;
      imageContainer.appendChild(errorMsg);
    };

    imageContainer.appendChild(img);
    wrapper.appendChild(imageContainer);

    // Add zoom controls
    this.setupZoom(img, imageContainer);
  }

  /**
   * Setup image zoom functionality
   */
  private setupZoom(img: HTMLImageElement, container: HTMLElement): void {
    let scale = 1;
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let translateX = 0;
    let translateY = 0;

    const updateTransform = () => {
      img.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    };

    // Zoom with mouse wheel
    container.addEventListener("wheel", (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      scale = Math.max(0.1, Math.min(10, scale * delta));
      updateTransform();
    });

    // Pan with mouse drag
    img.addEventListener("mousedown", (e) => {
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      img.style.cursor = "grabbing";
    });

    document.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      updateTransform();
    });

    document.addEventListener("mouseup", () => {
      isDragging = false;
      img.style.cursor = "grab";
    });

    // Reset on double-click
    img.addEventListener("dblclick", () => {
      scale = 1;
      translateX = 0;
      translateY = 0;
      updateTransform();
    });

    img.style.cursor = "grab";
  }
}
