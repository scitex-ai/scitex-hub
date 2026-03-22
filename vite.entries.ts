/**
 * Vite build entry points - auto-discovered from TypeScript source files.
 *
 * Convention: Files/dirs starting with '_' are internal and skipped.
 * Explicit overrides below handle entries where the template-referenced
 * name differs from the convention-based path.
 */
import { execSync } from "child_process";
import { resolve } from "path";
import * as path from "path";
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

/**
 * Discover TS entry points from pip-installed SciTeX packages.
 * Looks for static/<pkg_name>/ts/ in known package locations.
 */
const PIP_PACKAGES_WITH_STATIC = ["scitex_ui"];

function discoverPipEntries(rootDir: string): Record<string, string> {
  const entries: Record<string, string> = {};

  for (const pkgName of PIP_PACKAGES_WITH_STATIC) {
    try {
      const pkgDir = execSync(
        `python3 -c "import ${pkgName}; import os; print(os.path.dirname(${pkgName}.__file__))"`,
        { encoding: "utf-8" },
      ).trim();
      const tsDir = resolve(pkgDir, "static", pkgName, "ts");
      if (fs.existsSync(tsDir)) {
        Object.assign(
          entries,
          generateEntriesRecursive(pkgDir, `static/${pkgName}/ts`, pkgName),
        );
      }
    } catch {
      // Package not installed — skip silently
    }
  }
  return entries;
}

/**
 * Auto-discover bridge entry points from sibling app repositories.
 *
 * Scans sibling directories for manifest.json with a "bridge" key.
 * Entry name follows convention: "{app_name}/{slug}-bridge-init".
 */
function discoverBridgeEntries(rootDir: string): Record<string, string> {
  const entries: Record<string, string> = {};

  // Scan both sibling directories (local dev) and .apps/ (Docker/CI fallback)
  const searchDirs = [resolve(rootDir, ".."), resolve(rootDir, ".apps")].filter(
    (d) => fs.existsSync(d),
  );

  for (const parentDir of searchDirs) {
    for (const entry of fs.readdirSync(parentDir)) {
      if (entry.startsWith(".") || entry === path.basename(rootDir)) continue;
      const repoDir = resolve(parentDir, entry);
      try {
        if (!fs.statSync(repoDir).isDirectory()) continue;
      } catch {
        continue;
      }

      const pkgName = entry.replace(/-/g, "_");
      const manifestPaths = [
        resolve(repoDir, `src/${pkgName}/_django/manifest.json`),
        resolve(repoDir, "manifest.json"),
      ];

      for (const mp of manifestPaths) {
        if (!fs.existsSync(mp)) continue;
        try {
          const manifest = JSON.parse(fs.readFileSync(mp, "utf-8"));
          if (!manifest.bridge?.entry) continue;

          const slug = manifest.slug || pkgName;
          const appName = manifest.name || `${pkgName}_app`;
          const djangoDir = path.dirname(mp);
          const bridgeEntry = resolve(
            djangoDir,
            "frontend",
            manifest.bridge.entry,
          );

          if (fs.existsSync(bridgeEntry)) {
            entries[`${appName}/${slug}-bridge-init`] = bridgeEntry;
          }
          break;
        } catch {
          /* skip invalid manifests */
        }
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

    // Pip-installed SciTeX packages with static assets
    ...discoverPipEntries(rootDir),

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
    "shared/workspace-sidebar": r(
      rootDir,
      "static/shared/ts/components/sidebar/index.ts",
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

    // Auto-discovered app bridge entries from sibling repositories.
    // Each app declares its bridge entry in manifest.json.
    ...discoverBridgeEntries(rootDir),

    // Dev app scripts (standalone utilities — in scripts/ subdir, not ts/)
    "dev_app/scripts/design": r(
      rootDir,
      "apps/workspace/dev_app/static/dev_app/scripts/design.ts",
    ),
    "dev_app/scripts/scitex-icon-generator": r(
      rootDir,
      "apps/workspace/dev_app/static/dev_app/scripts/scitex-icon-generator.ts",
    ),

    // Run-stats tool (index.ts in subdir, template uses short name)
    "public_app/tools/run-stats": r(
      rootDir,
      "apps/infra/public_app/static/public_app/ts/tools/run-stats/index.ts",
    ),
  };
}
