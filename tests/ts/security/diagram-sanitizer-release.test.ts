/** The legacy global and the bundled sanitizer must be the same patched bytes. */
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { expect, it } from "vitest";

it("pins matching bundled/CDN DOMPurify with real npm payload integrity", () => {
  const declared = JSON.parse(readFileSync("package.json", "utf8"));
  const installed = JSON.parse(readFileSync("node_modules/dompurify/package.json", "utf8"));
  const template = readFileSync("templates/global_base_partials/global_body_scripts.html", "utf8");
  const scripts = [...template.matchAll(/<script[^>]+src="([^"]*dompurify[^\"]+)"[^>]+integrity="([^"]+)"/g)];
  expect(scripts).toHaveLength(1);
  expect(installed.version).toBe(declared.dependencies.dompurify);
  expect(scripts[0][1]).toBe(`https://cdn.jsdelivr.net/npm/dompurify@${installed.version}/dist/purify.min.js`);
  const bytes = readFileSync(resolve("node_modules/dompurify/dist/purify.min.js"));
  expect(scripts[0][2]).toBe(`sha384-${createHash("sha384").update(bytes).digest("base64")}`);
});
