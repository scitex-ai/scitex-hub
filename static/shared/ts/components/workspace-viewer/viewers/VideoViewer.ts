/**
 * VideoViewer - Simple HTML5 video player for video files.
 */

import type { Viewer } from "../types.ts";

export class VideoViewer implements Viewer {
  private video: HTMLVideoElement | null = null;

  async render(
    container: HTMLElement,
    filePath: string,
    projectId: string,
  ): Promise<void> {
    const rawUrl = `/console/api/file-content/${filePath}?project_id=${projectId}&raw=true`;
    const fileName = filePath.split("/").pop() || filePath;

    container.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.style.cssText =
      "display:flex; flex-direction:column; height:100%; overflow:hidden; background:#000;";

    const nameEl = document.createElement("div");
    nameEl.style.cssText =
      "padding:6px 10px; font-size:0.85em; color:#888; border-bottom:1px solid #222; flex-shrink:0;";
    nameEl.title = filePath;
    nameEl.textContent = fileName;

    const videoWrapper = document.createElement("div");
    videoWrapper.style.cssText =
      "flex:1; display:flex; align-items:center; justify-content:center; overflow:hidden;";

    this.video = document.createElement("video");
    this.video.controls = true;
    this.video.src = rawUrl;
    this.video.style.cssText =
      "max-width:100%; max-height:100%; display:block;";

    this.video.onerror = () => {
      const err = document.createElement("div");
      err.style.cssText =
        "color:#e55; font-size:0.9em; text-align:center; padding:20px;";
      err.textContent = `Failed to load video: ${fileName}`;
      videoWrapper.replaceChild(err, this.video!);
      this.video = null;
    };

    videoWrapper.appendChild(this.video);
    wrapper.appendChild(nameEl);
    wrapper.appendChild(videoWrapper);
    container.appendChild(wrapper);
  }

  destroy(): void {
    if (this.video) {
      this.video.pause();
      this.video.src = "";
      this.video = null;
    }
  }
}
