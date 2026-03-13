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

/**
 * Auto-discover TS entry points for all apps under apps/infra/ and apps/workspace/.
 * Convention: apps/<group>/<app_name>/static/<app_name>/ts/
 */
function discoverAppEntries(rootDir: string): Record<string, string> {
  const entries: Record<string, string> = {};
  const appsDir = resolve(rootDir, "apps");
  for (const group of ["infra", "workspace"]) {
    const groupDir = resolve(appsDir, group);
    if (!fs.existsSync(groupDir)) continue;
    for (const appName of fs.readdirSync(groupDir)) {
      if (appName.startsWith("_") || appName.startsWith(".")) continue;
      const tsDir = resolve(groupDir, appName, "static", appName, "ts");
      if (fs.existsSync(tsDir)) {
        Object.assign(
          entries,
          generateEntriesRecursive(
            rootDir,
            `apps/${group}/${appName}/static/${appName}/ts`,
            appName,
          ),
        );
      }
    }
  }
  return entries;
}

export function getEntryPoints(rootDir: string): Record<string, string> {
  return {
    // ── Auto-discovered entries ─────────────────────────────────
    // Shared: scans static/shared/ts/ recursively (components, utils, etc.)
    ...generateEntriesRecursive(rootDir, "static/shared/ts", "shared"),

    // App-specific entries: auto-discovered from apps/infra/ and apps/workspace/
    ...discoverAppEntries(rootDir),

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

    // figrecipe bridge (starts with '_', so auto-discovery skips it)
    // Only included when ../figrecipe exists (the alias resolves conditionally)
    ...(fs.existsSync(resolve(rootDir, "../figrecipe"))
      ? {
          "figrecipe_app/figrecipe-bridge-init": r(
            rootDir,
            "apps/workspace/figrecipe_app/static/figrecipe_app/ts/_figrecipe-bridge-init.ts",
          ),
        }
      : {}),

    // Dev app scripts (standalone utilities — in scripts/ subdir, not ts/)
    "dev_app/scripts/design": r(
      rootDir,
      "apps/workspace/dev_app/static/dev_app/scripts/design.ts",
    ),
    "dev_app/scripts/scitex-icon-generator": r(
      rootDir,
      "apps/workspace/dev_app/static/dev_app/scripts/scitex-icon-generator.ts",
    ),
  };
}
