/** Redirect only Monaco's vendored DOMPurify module, keeping upstream APIs. */
import { realpathSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
import type { Plugin } from "vite";

export function monacoSanitizerBoundary(root: string): Plugin {
  const vendor = realpathSync(resolve(root, "node_modules/monaco-editor/esm/vs/base/browser/dompurify/dompurify.js"));
  const adapter = resolve(root, "static/shared/ts/utils/monaco-sanitizer.ts");
  return {
    name: "scitex-monaco-sanitizer-boundary",
    enforce: "pre",
    async resolveId(source, importer) {
      if (!importer) return null;
      let path: string;
      if (source.startsWith(".") || isAbsolute(source)) {
        path = resolve(dirname(importer.split("?")[0]), source.split("?")[0]);
      } else if (source === "monaco-editor/esm/vs/base/browser/dompurify/dompurify.js") {
        const resolved = await this.resolve(source, importer, { skipSelf: true });
        if (!resolved || resolved.external) return null;
        path = resolved.id.split("?")[0];
      } else {
        return null;
      }
      // realpath admits only the selected, installed root Monaco module. A
      // similarly named file in another package never acquires this binding.
      try {
        return realpathSync(path) === vendor ? adapter : null;
      } catch {
        return null;
      }
    },
  };
}
