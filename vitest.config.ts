import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    include: ["tests/custom/ts/**/*.test.ts"],
    exclude: ["node_modules", "GITIGNORED/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      reportsDirectory: "./coverage/ts",
    },
  },
  resolve: {
    alias: {
      // Shared-source alias (mirrors vite.config.ts "@" → static/shared/ts) so
      // writer/console/etc. source files that import "@/utils/..." resolve
      // under vitest.
      "@": path.resolve(__dirname, "static/shared/ts"),
      // App aliases for imports
      "@apps_app": path.resolve(
        __dirname,
        "apps/workspace/apps_app/static/apps_app/ts",
      ),
      "@figrecipe_app": path.resolve(
        __dirname,
        "apps/workspace/figrecipe_app/static/figrecipe_app/ts",
      ),
      "@console_app": path.resolve(
        __dirname,
        "apps/workspace/console_app/static/console_app/ts",
      ),
      "@project_app": path.resolve(
        __dirname,
        "apps/infra/project_app/static/project_app/ts",
      ),
      "@scholar_app": path.resolve(
        __dirname,
        "apps/workspace/scholar_app/static/scholar_app/ts",
      ),
      "@writer_app": path.resolve(
        __dirname,
        "apps/workspace/writer_app/static/writer_app/ts",
      ),
      "@public_app": path.resolve(
        __dirname,
        "apps/infra/public_app/static/public_app/ts",
      ),
      "@shared": path.resolve(__dirname, "static/shared/ts"),
    },
  },
});
