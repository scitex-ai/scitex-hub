/**
 * Vite build entry points - auto-discovered from TypeScript source files.
 *
 * Convention: Files/dirs starting with '_' are internal and skipped.
 * Explicit overrides below handle entries where the template-referenced
 * name differs from the convention-based path.
 */
import { resolve } from "path";
import * as fs from "fs";

/** Directories to skip during auto-discovery */
const SKIP_DIRS = new Set(["types", "interfaces", "node_modules", "__tests__"]);

/**
 * Recursively scan a directory for .ts entry points.
 * Skips: files/dirs starting with '_', .d.ts files, and SKIP_DIRS.
 */
export function generateEntriesRecursive(
  rootDir: string,
  dir: string,
  prefix: string,
): Record<string, string> {
  const entries: Record<string, string> = {};
  const fullDir = resolve(rootDir, dir);
  if (!fs.existsSync(fullDir)) return entries;

  function scan(currentDir: string, currentPrefix: string) {
    const items = fs.readdirSync(currentDir, { withFileTypes: true });
    for (const item of items) {
      if (item.name.startsWith("_") || item.name.startsWith(".")) continue;
      if (item.isDirectory()) {
        if (SKIP_DIRS.has(item.name)) continue;
        scan(resolve(currentDir, item.name), `${currentPrefix}/${item.name}`);
      } else if (
        item.isFile() &&
        (item.name.endsWith(".ts") || item.name.endsWith(".tsx")) &&
        !item.name.endsWith(".d.ts")
      ) {
        const name = item.name.replace(/\.tsx?$/, "");
        entries[`${currentPrefix}/${name}`] = resolve(currentDir, item.name);
      }
    }
  }

  scan(fullDir, prefix);
  return entries;
}

/** Helper to resolve paths relative to root */
function r(rootDir: string, path: string): string {
  return resolve(rootDir, path);
}

export function getEntryPoints(rootDir: string): Record<string, string> {
  return {
    // ── Auto-discovered entries ─────────────────────────────────
    // Shared: scans static/shared/ts/ recursively (components, utils, etc.)
    ...generateEntriesRecursive(rootDir, "static/shared/ts", "shared"),

    // App-specific entries
    ...generateEntriesRecursive(
      rootDir,
      "apps/console_app/static/console_app/ts",
      "console_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/vis_app/static/vis_app/ts",
      "vis_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/writer_app/static/writer_app/ts",
      "writer_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/project_app/static/project_app/ts",
      "project_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/scholar_app/static/scholar_app/ts",
      "scholar_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/public_app/static/public_app/ts",
      "public_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/accounts_app/static/accounts_app/ts",
      "accounts_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/hub_app/static/hub_app/ts",
      "hub_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/clew_app/static/clew_app/ts",
      "clew_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/social_app/static/social_app/ts",
      "social_app",
    ),
    ...generateEntriesRecursive(
      rootDir,
      "apps/docs_app/static/docs_app/ts",
      "docs_app",
    ),

    // ── Explicit overrides ──────────────────────────────────────
    // These entries have template names that differ from convention.
    // Later entries override earlier ones with the same key.

    // Naming mismatches: template name ≠ auto-discovered path
    "shared/workspace-tree-init": r(
      rootDir,
      "static/shared/ts/components/workspace-files-tree/auto-init.ts",
    ),
    "shared/workspace-viewer-init": r(
      rootDir,
      "static/shared/ts/components/workspace-viewer/init.ts",
    ),
    "shared/workspace-panel-resizer": r(
      rootDir,
      "static/shared/ts/components/workspace-panel-resizer.ts",
    ),
    "shared/collapsible-panel-click-expand": r(
      rootDir,
      "static/shared/ts/components/collapsible-panel-click-expand.ts",
    ),
    "shared/resizer": r(
      rootDir,
      "static/shared/ts/components/resizer/index.ts",
    ),
    "shared/repo-monitor": r(
      rootDir,
      "static/shared/ts/components/repo-monitor/index.ts",
    ),

    // Non-standard static directory structure
    "workspace_app/workspace-shell": r(
      rootDir,
      "static/workspace_app/ts/workspace-shell.ts",
    ),

    // Dev app scripts (standalone utilities)
    "dev_app/scripts/design": r(
      rootDir,
      "apps/dev_app/static/dev_app/scripts/design.ts",
    ),
    "dev_app/scripts/scitex-icon-generator": r(
      rootDir,
      "apps/dev_app/static/dev_app/scripts/scitex-icon-generator.ts",
    ),
  };
}
