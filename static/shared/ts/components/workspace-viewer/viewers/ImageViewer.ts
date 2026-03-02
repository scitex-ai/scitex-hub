/**
 * ImageViewer - Displays images with zoom (wheel) and pan (drag).
 * Double-click resets to original position and scale.
 */

import type { Viewer } from "../types";
import { getFileUrl } from "../_file-loader";

export class ImageViewer implements Viewer {
  private listeners: Array<{
    target: EventTarget;
    type: string;
    fn: EventListener;
  }> = [];

  async render(
    container: HTMLElement,
    filePath: string,
    projectId: string,
  ): Promise<void> {
    const rawUrl = getFileUrl(filePath, projectId, true);
    const fileName = filePath.split("/").pop() || filePath;

    container.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.style.cssText =
      "display:flex; flex-direction:column; height:100%; overflow:hidden;";

    const toolbar = document.createElement("div");
    toolbar.style.cssText =
      "padding:6px 10px; font-size:0.85em; color:#888; border-bottom:1px solid #333; flex-shrink:0;";
    toolbar.textContent = fileName;
    wrapper.appendChild(toolbar);

    const imageContainer = document.createElement("div");
    imageContainer.style.cssText =
      "flex:1; overflow:hidden; position:relative; cursor:grab; background:#1a1a1a;";

    const img = document.createElement("img");
    img.alt = fileName;
    img.src = rawUrl;
    img.style.cssText =
      "position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); max-width:100%; max-height:100%; transform-origin:center center; user-select:none;";

    img.onerror = () => {
      img.remove();
      const err = document.createElement("div");
      err.style.cssText = "padding:20px; color:#e55; text-align:center;";
      err.textContent = `Failed to load image: ${fileName}`;
      imageContainer.appendChild(err);
    };

    imageContainer.appendChild(img);
    wrapper.appendChild(imageContainer);
    container.appendChild(wrapper);

    this.setupZoomPan(img, imageContainer);
  }

  private setupZoomPan(img: HTMLImageElement, container: HTMLElement): void {
    let scale = 1;
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let translateX = 0;
    let translateY = 0;

    const updateTransform = () => {
      img.style.transform = `translate(calc(-50% + ${translateX}px), calc(-50% + ${translateY}px)) scale(${scale})`;
    };

    const onWheel = (e: Event) => {
      e.preventDefault();
      const we = e as WheelEvent;
      const delta = we.deltaY > 0 ? 0.9 : 1.1;
      scale = Math.max(0.1, Math.min(10, scale * delta));
      updateTransform();
    };

    const onMouseDown = (e: Event) => {
      const me = e as MouseEvent;
      isDragging = true;
      startX = me.clientX - translateX;
      startY = me.clientY - translateY;
      container.style.cursor = "grabbing";
    };

    const onMouseMove = (e: Event) => {
      if (!isDragging) return;
      const me = e as MouseEvent;
      translateX = me.clientX - startX;
      translateY = me.clientY - startY;
      updateTransform();
    };

    const onMouseUp = () => {
      isDragging = false;
      container.style.cursor = "grab";
    };

    const onDblClick = () => {
      scale = 1;
      translateX = 0;
      translateY = 0;
      updateTransform();
    };

    container.addEventListener("wheel", onWheel, { passive: false });
    img.addEventListener("mousedown", onMouseDown);
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    img.addEventListener("dblclick", onDblClick);

    this.listeners.push(
      { target: container, type: "wheel", fn: onWheel as EventListener },
      { target: img, type: "mousedown", fn: onMouseDown as EventListener },
      { target: document, type: "mousemove", fn: onMouseMove as EventListener },
      { target: document, type: "mouseup", fn: onMouseUp as EventListener },
      { target: img, type: "dblclick", fn: onDblClick as EventListener },
    );
  }

  destroy(): void {
    for (const { target, type, fn } of this.listeners) {
      target.removeEventListener(type, fn);
    }
    this.listeners = [];
  }
}
