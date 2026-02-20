import { defineConfig, Plugin } from "vite";
import { resolve } from "path";
import * as fs from "fs";
import { getEntryPoints } from "./vite.entries";

/**
 * Plugin to resolve /static/ absolute paths to actual file locations
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
        if (fs.existsSync(fullPath)) {
          return fullPath;
        }
        const match = source.match(/^\/static\/(\w+_app)\/(.*)/);
        if (match) {
          const [, appName, rest] = match;
          const appPath = `apps/${appName}/static/${appName}/${rest}`;
          const appFullPath = resolve(__dirname, appPath);
          if (fs.existsSync(appFullPath)) {
            return appFullPath;
          }
        }
      }

      return null;
    },
  };
}

export default defineConfig({
  plugins: [resolveStaticPaths()],
  base: "/",
  root: ".",
  publicDir: false,

  resolve: {
    alias: {
      "@": resolve(__dirname, "static/shared/ts"),
      "@types": resolve(__dirname, "static/shared/ts/types"),
      "@utils": resolve(__dirname, "static/shared/ts/utils"),
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
      interval: 3000,
    },
    fs: {
      allow: ["."],
    },
    warmup: {
      clientFiles: [
        "apps/console_app/static/console_app/ts/workspace.ts",
        "apps/console_app/static/console_app/ts/workspace/**/*.ts",
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

  optimizeDeps: {
    include: ["fabric"],
  },
});
