/**
 * vite.config.app.ts — Container-only Vite for dev app development.
 *
 * Runs on port 5174 inside the Docker container.
 * Only watches dev app TypeScript files (data/users/*/ proj; /*/static/).
 * Platform files are handled by host Vite on port 5173.
 */
import { defineConfig } from "vite";
import { resolve } from "path";
import * as fs from "fs";
import * as path from "path";

/**
 * Auto-discover TypeScript entry points from dev app directories.
 * Scans: data/users/<owner>/proj/<repo>/static/<app_name>/ts/*.ts
 */
function getDevAppEntries(rootDir: string): Record<string, string> {
  const entries: Record<string, string> = {};
  const dataDir = resolve(rootDir, "data/users");

  if (!fs.existsSync(dataDir)) return entries;

  for (const owner of safeReaddir(dataDir)) {
    const projDir = resolve(dataDir, owner, "proj");
    if (!fs.existsSync(projDir)) continue;

    for (const repo of safeReaddir(projDir)) {
      const staticDir = resolve(projDir, repo, "static");
      if (!fs.existsSync(staticDir)) continue;

      for (const appName of safeReaddir(staticDir)) {
        const tsDir = resolve(staticDir, appName, "ts");
        if (!fs.existsSync(tsDir)) continue;

        scanDir(tsDir, appName, entries);
      }
    }
  }

  return entries;
}

function safeReaddir(dir: string): string[] {
  try {
    return fs
      .readdirSync(dir, { withFileTypes: true })
      .filter((d) => d.isDirectory() && !d.name.startsWith("."))
      .map((d) => d.name);
  } catch {
    return [];
  }
}

function scanDir(
  dir: string,
  prefix: string,
  entries: Record<string, string>,
): void {
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    if (item.name.startsWith("_") || item.name.startsWith(".")) continue;

    const fullPath = resolve(dir, item.name);
    if (item.isDirectory()) {
      scanDir(fullPath, `${prefix}/${item.name}`, entries);
    } else if (item.name.endsWith(".ts") && !item.name.endsWith(".d.ts")) {
      const name = item.name.replace(/\.ts$/, "");
      entries[`${prefix}/${name}`] = fullPath;
    }
  }
}

const devEntries = getDevAppEntries(__dirname);
const hasEntries = Object.keys(devEntries).length > 0;

if (hasEntries) {
  console.log(
    `[vite:app] Found ${Object.keys(devEntries).length} dev app entries:`,
  );
  for (const [name, filepath] of Object.entries(devEntries)) {
    console.log(`  ${name} → ${path.relative(__dirname, filepath)}`);
  }
} else {
  console.log("[vite:app] No dev app TypeScript files found.");
}

export default defineConfig({
  root: ".",
  publicDir: false,
  logLevel: "info",

  server: {
    port: 5174,
    strictPort: true,
    host: "0.0.0.0",
    hmr: {
      port: 5174,
      host: "127.0.0.1",
    },
    cors: true,
    watch: {
      usePolling: true,
      interval: 3000,
      ignored: [
        "**/node_modules/**",
        "**/deployment/**",
        "**/docs/**",
        "**/GITIGNORED/**",
        "**/apps/**",
        "**/static/shared/**",
        "**/static/workspace_app/**",
        "**/*.py",
        "**/*.md",
        "**/*.json",
        "**/*.yaml",
        "**/*.sh",
        "**/*.html",
      ],
    },
    fs: {
      allow: ["."],
    },
  },

  build: {
    outDir: "staticfiles/vite-app",
    manifest: true,
    rollupOptions: {
      input: devEntries,
      output: {
        entryFileNames: "[name]-[hash].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});
