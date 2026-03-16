import react from "@vitejs/plugin-react";
import { defineConfig, Plugin } from "vite";
import { resolve } from "path";
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
      // Exclude external figrecipe source from Fast Refresh (avoids preamble error).
      // esbuild still handles JSX via tsconfig "jsx": "react-jsx".
      exclude: [/figrecipe/, /figrecipe_app/, /scitex.ui/],
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
      // scitex-ui: shared component library (auto-discovered from pip)
      ...(SCITEX_UI_STATIC ? { "scitex-ui": SCITEX_UI_STATIC } : {}),
      // Only include figrecipe alias if figrecipe directory exists (dev only)
      ...(fs.existsSync(resolve(__dirname, "../figrecipe"))
        ? {
            "figrecipe-editor": resolve(
              __dirname,
              "../figrecipe/src/figrecipe/_django/frontend/src",
            ),
          }
        : {}),
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
      host: "127.0.0.1",
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
        resolve(__dirname, "../figrecipe"),
        ...(SCITEX_UI_STATIC ? [SCITEX_UI_STATIC] : []),
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
    include: ["fabric", "react", "react-dom"],
    exclude: ["figrecipe-editor"],
  },
});
