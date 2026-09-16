/**
 * URL for an in-app navigation state (app-navigation-history.ts).
 *
 * Pure so it can be tested without the history singleton.
 *
 * Module pages keep their module URL (/apps/<module>/ or
 * /apps/workspace/<module>/). A project page (/<owner>/<slug>/..., the file
 * tree Project UI) is NOT a module: opening a file there points the URL at
 * that file's /blob/ deep link, so the address bar is a shareable link to what
 * is on screen. It used to be rewritten to /apps/<owner>/ — the owner segment
 * mistaken for a module name — which dropped the project and the path (site
 * audit 2026-09-14, D12).
 */

export interface NavUrlState {
  module: string;
  file?: string;
}

export interface NavUrlLocation {
  pathname: string;
  search: string;
}

/**
 * @param loc          current location (pathname + search)
 * @param state        navigation state being pushed/replaced
 * @param projectBase  "/<owner>/<slug>/" of the project whose tree is on the
 *                     page, or null when the page shows no project tree
 */
export function buildNavUrl(
  loc: NavUrlLocation,
  state: NavUrlState,
  projectBase: string | null,
): string {
  const { pathname, search } = loc;
  if (pathname.startsWith("/apps/workspace/")) {
    return `/apps/workspace/${state.module}/`;
  }
  if (pathname.startsWith("/apps/") || pathname.startsWith("/workspace/")) {
    const routeSlugs: Record<string, string> = {
      my_projects: "my-projects",
      public_projects: "public-projects",
    };
    return `/apps/${routeSlugs[state.module] ?? state.module}/`;
  }
  if (projectBase && pathname.startsWith(projectBase)) {
    if (!state.file) return pathname + search;
    const encoded = state.file
      .replace(/^\/+/, "")
      .split("/")
      .map(encodeURIComponent)
      .join("/");
    return `${projectBase}blob/${encoded}`;
  }
  // Any other page: leave its URL alone rather than invent a module URL.
  return pathname + search;
}
