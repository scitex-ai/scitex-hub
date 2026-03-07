/**
 * Module Icon Builder — TypeScript counterpart of module_icons.py.
 *
 * Single source of truth for building module icon HTML on the client side.
 * Mirrors the Python build_module_icon_html() function exactly.
 *
 * Usage:
 *   import { buildModuleIconHtml } from "../utils/module-icon";
 *   el.innerHTML = buildModuleIconHtml({ icon: "fas fa-puzzle-piece", isPrivate: true });
 */

/** Version suffix → badge CSS class + label */
const BADGE_MAP: Record<string, [string, string]> = {
  "-dev": ["module-status-badge--dev", "DEV"],
  "-alpha": ["module-status-badge--alpha", "\u03b1"], // α
  "-beta": ["module-status-badge--beta", "\u03b2"], // β
};

export interface ModuleIconOptions {
  /** FontAwesome class, e.g. "fas fa-puzzle-piece" */
  icon: string;
  /** Version string, e.g. "0.1.0-alpha" — suffix determines badge */
  version?: string;
  /** Show lock overlay for private (non-published) apps */
  isPrivate?: boolean;
}

/**
 * Build canonical module icon HTML with badge overlay.
 *
 * This is the client-side equivalent of Python's build_module_icon_html().
 * Both produce identical HTML structure.
 */
export function buildModuleIconHtml(opts: ModuleIconOptions): string {
  const iconHtml = `<i class="${opts.icon}"></i>`;
  const badgeHtml = resolveBadgeHtml(
    opts.version || "",
    opts.isPrivate || false,
  );

  if (badgeHtml) {
    return `<span class="module-icon-wrap">${iconHtml}${badgeHtml}</span>`;
  }
  return iconHtml;
}

function resolveBadgeHtml(version: string, isPrivate: boolean): string {
  if (isPrivate) {
    return '<i class="fas fa-lock module-private-lock"></i>';
  }
  for (const [suffix, [cssCls, label]] of Object.entries(BADGE_MAP)) {
    if (version.endsWith(suffix)) {
      return `<span class="module-status-badge ${cssCls}">${label}</span>`;
    }
  }
  return "";
}
