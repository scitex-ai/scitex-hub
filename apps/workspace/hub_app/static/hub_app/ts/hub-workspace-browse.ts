/**
 * Hub workspace file browser — tabs, file/directory browsing, dynamic area.
 * Extracted from index.ts to keep file size under 512 lines.
 */

import { hubGet } from "./hub-api";
import { getBranch, pushProjectUrl } from "./hub-url";

let currentTab = "files";

export async function switchHubTab(
  tab: string,
  container: HTMLElement,
): Promise<void> {
  currentTab = tab;
  container
    .querySelectorAll(".hub-tab")
    .forEach((t) => t.classList.remove("scitex-tab-active"));
  container
    .querySelector(`[data-hub-tab="${tab}"]`)
    ?.classList.add("scitex-tab-active");
  const toolbar = container.querySelector(
    "#hub-files-toolbar",
  ) as HTMLElement | null;
  if (toolbar) toolbar.style.display = tab === "files" ? "" : "none";
  if (tab === "files") {
    loadHubBrowse("", container);
  } else {
    pushProjectUrl(tab);
    await loadHubTabContent(tab, container);
  }
}

export async function loadHubTabContent(
  tab: string,
  container: HTMLElement,
  qs?: string,
): Promise<void> {
  const target = getDynamicArea(container);
  target.style.opacity = "0.5";
  const data = await hubGet(`/hub/api/${tab}/${qs ? `?${qs}` : ""}`);
  if (data?.success) target.innerHTML = data.html;
  target.style.opacity = "1";
}

export async function loadHubBrowse(
  path: string,
  container: HTMLElement,
): Promise<void> {
  const target = getDynamicArea(container);
  target.style.opacity = "0.5";
  if (path) pushProjectUrl(`tree/${getBranch()}/${path}`);
  else pushProjectUrl();
  const data = await hubGet(
    `/hub/api/browse/?path=${encodeURIComponent(path)}`,
  );
  if (data?.success) {
    target.innerHTML = data.html;
    postLoadHooks();
  }
  target.style.opacity = "1";
}

export async function loadHubFile(
  path: string,
  container: HTMLElement,
): Promise<void> {
  const target = getDynamicArea(container);
  target.style.opacity = "0.5";
  pushProjectUrl(`blob/${getBranch()}/${path}`);
  const data = await hubGet(`/hub/api/file/?path=${encodeURIComponent(path)}`);
  if (data?.success) target.innerHTML = data.html;
  target.style.opacity = "1";
}

export function extractRelPath(href: string): string {
  const parts = href.replace(/^\/|\/$/g, "").split("/");
  return parts.length <= 2 ? "" : parts.slice(2).join("/");
}

export function extractFileRelPath(href: string): string {
  const parts = href.replace(/^\/|\/$/g, "").split("/");
  const blobIdx = parts.indexOf("blob");
  if (blobIdx >= 0 && blobIdx + 1 < parts.length)
    return parts.slice(blobIdx + 1).join("/");
  return parts.length <= 2 ? "" : parts.slice(2).join("/");
}

function getDynamicArea(container: HTMLElement): HTMLElement {
  let target = container.querySelector(
    ".hub-browse-dynamic",
  ) as HTMLElement | null;
  if (target) return target;
  const fileBrowser = container.querySelector(".file-browser");
  const readme = container.querySelector(".readme-container");
  const wrapper = document.createElement("div");
  wrapper.className = "hub-browse-dynamic";
  if (fileBrowser) {
    fileBrowser.replaceWith(wrapper);
    wrapper.appendChild(fileBrowser);
    if (readme) {
      readme.remove();
      wrapper.appendChild(readme);
    }
  } else {
    container.appendChild(wrapper);
  }
  return wrapper;
}

function postLoadHooks(): void {
  const showHidden =
    localStorage.getItem("scitex-show-hidden-files") === "true";
  document.querySelectorAll<HTMLElement>(".file-browser-row").forEach((row) => {
    const name = (row.dataset.path || "").split("/").pop() || "";
    if (name.startsWith(".")) row.style.display = showHidden ? "" : "none";
  });
}
