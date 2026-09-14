/** Shared types and small DOM/format helpers for the Files app. */

export interface Entry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified: number;
  project_url: string;
}

export type Strings = Record<string, string>;

export const API = "/apps/files/";
export const IMAGE = /\.(png|jpe?g|gif|webp|bmp|avif)$/i;
export const VIDEO = /\.(mp4|webm|mov|m4v|ogv)$/i;
export const AUDIO = /\.(mp3|wav|ogg|m4a|flac)$/i;
export const PDF = /\.pdf$/i;
export const TEXT =
  /\.(txt|md|csv|tsv|json|ya?ml|py|r|m|tex|bib|log|sh|toml|ini|cfg|xml|html|css|js|ts|svg)$/i;

export function byId<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

export function fmt(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/%\((\w+)\)s/g, (_m, key) =>
    String(values[key] ?? ""),
  );
}

export function humanSize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit === 0 ? value : value.toFixed(1)} ${units[unit]}`;
}

export function iconFor(entry: Entry): string {
  if (entry.is_dir) {
    if (entry.path === "Downloads") return "fa-download";
    if (entry.path === "Recordings") return "fa-video";
    return "fa-folder";
  }
  if (IMAGE.test(entry.name)) return "fa-file-image";
  if (VIDEO.test(entry.name)) return "fa-file-video";
  if (AUDIO.test(entry.name)) return "fa-file-audio";
  if (PDF.test(entry.name)) return "fa-file-pdf";
  if (TEXT.test(entry.name)) return "fa-file-lines";
  return "fa-file";
}

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
  text = "",
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

export function query(path: string): string {
  return `?path=${encodeURIComponent(path)}`;
}

export function iconLabel<T extends HTMLElement>(
  node: T,
  icon: string,
  label: string,
): T {
  const i = el("i", `fas ${icon}`);
  i.setAttribute("aria-hidden", "true");
  node.append(i, el("span", "", label));
  return node;
}

export function linkButton(
  label: string,
  icon: string,
  href: string,
): HTMLAnchorElement {
  const link = el("a", "files-btn");
  link.href = href;
  return iconLabel(link, icon, label);
}
