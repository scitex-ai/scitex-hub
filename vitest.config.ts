import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    include: ["tests/ts/**/*.test.ts"],
    exclude: ["node_modules", "GITIGNORED/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      reportsDirectory: "./coverage/ts",
    },
  },
  resolve: {
    alias: {
      // App aliases for imports
      "@vis_app": path.resolve(__dirname, "apps/workspace/vis_app/static/vis_app/ts"),
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
