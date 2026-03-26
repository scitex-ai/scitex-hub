import react from "@vitejs/plugin-react";
import { defineConfig, Plugin } from "vite";
import { resolve } from "path";
import * as path from "path";
import * as fs from "fs";
import { execSync } from "child_process";
import { getEntryPoints } from "./vite.entries";

/**
 * Discover scitex-ui static directory from the Python environment.
 * Same pattern as figrecipe/vite.config.ts — works for pip and editable installs.
 */
function discoverScitexUiStatic(): string | null {
  if (process.env.SCITEX_UI_STATIC) {
    return process.env.SCITEX_UI_STATIC;
  }

  // Prefer .apps/scitex-ui (has node_modules for npm deps like mermaid)
  // then sibling ../scitex-ui, then pip-installed location
  const candidates = [
    resolve(__dirname, ".apps/scitex-ui/src/scitex_ui/static/scitex_ui"),
    resolve(__dirname, "../scitex-ui/src/scitex_ui/static/scitex_ui"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }

  try {
    return execSync(
      'python3 -c "import scitex_ui; print(scitex_ui.get_static_dir())"',
      { encoding: "utf-8", timeout: 5000 },
    ).trim();
  } catch {
    return null;
  }
}

const SCITEX_UI_STATIC = discoverScitexUiStatic();

/** Discovered app bridge configuration. */
interface AppBridgeInfo {
  slug: string;
  appName: string;
  repoDir: string;
  frontendSrc: string;
}

/**
 * Auto-discover app bridges from sibling repositories.
 *
 * Scans sibling directories for manifest.json files with a "bridge" key.
 * Returns Vite aliases, fs.allow entries, and exclude patterns.
 */
function discoverAppBridges(rootDir: string): {
  aliases: Record<string, string>;
  fsAllow: string[];
  excludePatterns: RegExp[];
  bridges: AppBridgeInfo[];
} {
  const aliases: Record<string, string> = {};
  const fsAllow: string[] = [];
  const excludePatterns: RegExp[] = [];
  const bridges: AppBridgeInfo[] = [];

  // Scan both sibling directories (local dev) and .apps/ (Docker/CI fallback)
  const searchDirs = [resolve(rootDir, ".."), resolve(rootDir, ".apps")].filter(
    (d) => fs.existsSync(d),
  );

  if (searchDirs.length === 0)
    return { aliases, fsAllow, excludePatterns, bridges };

  for (const parentDir of searchDirs) {
    for (const entry of fs.readdirSync(parentDir)) {
      if (entry.startsWith(".") || entry === path.basename(rootDir)) continue;
      const repoDir = resolve(parentDir, entry);
      try {
        if (!fs.statSync(repoDir).isDirectory()) continue;
      } catch {
        continue;
      }

      // Derive Python package name from repo name (e.g. "figrecipe" → "figrecipe")
      const pkgName = entry.replace(/-/g, "_");

      // Look for manifest.json in _django/ subdirectory
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
          const frontendSrc = resolve(djangoDir, "frontend", "src");

          if (!fs.existsSync(frontendSrc)) continue;

          // Add Vite alias: "{slug}-editor" → frontend source
          aliases[`${slug}-editor`] = frontendSrc;
          fsAllow.push(repoDir);
          excludePatterns.push(new RegExp(slug));
          bridges.push({ slug, appName, repoDir, frontendSrc });
          break;
        } catch {
          /* skip invalid manifests */
        }
      }
    }
  } // end searchDirs loop

  return { aliases, fsAllow, excludePatterns, bridges };
}

const APP_BRIDGES = discoverAppBridges(__dirname);

/**
 * Resolve an app's static directory, searching infra/ and workspace/ groups.
 * Returns the full path if found, or null.
 */
function findAppStaticPath(appName: string, rest: string): string | null {
  for (const group of ["infra", "workspace", ""]) {
    const appPath = group
      ? `apps/${group}/${appName}/static/${appName}/${rest}`
      : `apps/${appName}/static/${appName}/${rest}`;
    const fullPath = resolve(__dirname, appPath);
    if (fs.existsSync(fullPath)) return fullPath;
  }
  return null;
}

/**
 * Plugin to resolve /static/ absolute paths to actual file locations.
 * Handles apps reorganized into apps/infra/ and apps/workspace/.
 */
function resolveStaticPaths(): Plugin {
  return {
    name: "resolve-static-paths",
    enforce: "pre",
    resolveId(source) {
      if (source.includes("node_modules") || source.startsWith("http"))
        return null;

      if (source.startsWith("/static/")) {
        const mappedPath = source.replace("/static/", "static/");
        const fullPath = resolve(__dirname, mappedPath);
        if (fs.existsSync(fullPath)) return fullPath;

        const match = source.match(/^\/static\/(\w+_app)\/(.*)/);
        if (match) {
          const [, appName, rest] = match;
          const found = findAppStaticPath(appName, rest);
          if (found) return found;
        }
      }

      return null;
    },
  };
}

export default defineConfig({
  plugins: [
    react({
      // Exclude external app sources from Fast Refresh (avoids preamble error).
      // esbuild still handles JSX via tsconfig "jsx": "react-jsx".
      exclude: [/scitex.ui/, ...APP_BRIDGES.excludePatterns],
    }),
    resolveStaticPaths(),
  ],
  base: "/",
  root: ".",
  publicDir: false,

  resolve: {
    alias: {
      "@": resolve(__dirname, "static/shared/ts"),
      "@types": resolve(__dirname, "static/shared/ts/types"),
      "@utils": resolve(__dirname, "static/shared/ts/utils"),
      // Ensure monaco-editor resolves from scitex-cloud's node_modules
      // even when imported from scitex-ui files outside this directory tree
      "monaco-editor": resolve(__dirname, "node_modules/monaco-editor"),
      // Ensure mermaid resolves from scitex-cloud's node_modules
      // even when dynamically imported from symlinked scitex-ui files
      mermaid: resolve(__dirname, "node_modules/mermaid"),
      // scitex-ui: shared component library (auto-discovered)
      ...(SCITEX_UI_STATIC
        ? {
            "scitex-ui": SCITEX_UI_STATIC,
            // @scitex/ui is the npm package name used by figrecipe's frontend
            // imports like @scitex/ui/src/scitex_ui/static/... resolve from repo root
            "@scitex/ui": resolve(SCITEX_UI_STATIC, "../../../.."),
          }
        : {}),
      // Auto-discovered app bridges (e.g. "figrecipe-editor" → sibling repo)
      ...APP_BRIDGES.aliases,
    },
    extensions: [".ts", ".js", ".tsx", ".jsx", ".json"],
  },

  logLevel: "warn",

  server: {
    port: 5173,
    host: "0.0.0.0",
    strictPort: true,
    hmr: {
      port: 5173,
      // No host specified — Vite auto-detects from the page URL.
      // This allows LAN access (iPhone dev testing via Windows IP).
    },
    cors: true,
    watch: {
      usePolling: true,
      interval: 5000,
      ignored: [
        "**/deployment/singularity/**",
        "**/singularity/**",
        "**/node_modules/**",
        "**/docs/**",
        "**/data/**",
        "**/GITIGNORED/**",
        "**/.claude/**",
        "**/mgmt/**",
        "**/releases/**",
        "**/scripts/**",
        "**/tests/**",
        "**/config/**",
        "**/apps/**/views/**",
        "**/apps/**/models/**",
        "**/apps/**/services/**",
        "**/apps/**/serializers/**",
        "**/apps/**/urls.py",
        "**/apps/**/admin.py",
        "**/*.py",
        "**/*.md",
        "**/*.json",
        "**/*.yaml",
        "**/*.yml",
        "**/*.sh",
        "**/*.html",
      ],
    },
    fs: {
      allow: [
        ".",
        ...(SCITEX_UI_STATIC ? [SCITEX_UI_STATIC] : []),
        // Auto-discovered app repos
        ...APP_BRIDGES.fsAllow,
      ],
    },
    warmup: {
      clientFiles: [
        "apps/workspace/console_app/static/console_app/ts/workspace.ts",
        "apps/workspace/console_app/static/console_app/ts/workspace/**/*.ts",
      ],
    },
  },

  build: {
    outDir: "staticfiles/vite",
    manifest: true,
    rollupOptions: {
      input: getEntryPoints(__dirname),
      // @hpcc-js/wasm-graphviz is loaded at runtime by GraphvizViewer;
      // it ships WASM blobs that Rollup cannot bundle.
      external: ["@hpcc-js/wasm-graphviz"],
      output: {
        entryFileNames: "[name]-[hash].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },

  esbuild: {
    jsx: "automatic",
  },

  optimizeDeps: {
    include: ["fabric", "react", "react-dom", "mermaid"],
    // Exclude auto-discovered app editor aliases from pre-bundling
    exclude: Object.keys(APP_BRIDGES.aliases),
  },
});
