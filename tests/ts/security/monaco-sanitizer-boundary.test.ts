/** Exact installed-module ownership, real sanitizer behavior and hook isolation. */
import { readFileSync, realpathSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, expect, it } from "vitest";
import shared from "dompurify";
import * as adapter from "@/utils/monaco-sanitizer";
import { monacoSanitizerBoundary } from "../../../vite.monaco-sanitizer";

afterEach(() => { adapter.clearConfig(); adapter.removeAllHooks(); });

it("preserves the actual installed vendor export surface at the patched version", () => {
  const vendor = readFileSync("node_modules/monaco-editor/esm/vs/base/browser/dompurify/dompurify.js", "utf8");
  const names = [...vendor.matchAll(/^export (?:const (\w+)|default)/gm)].map(row => row[1] ?? "default");
  expect(Object.keys(adapter).sort()).toEqual(names.sort());
  expect(adapter.version).toBe(JSON.parse(readFileSync("node_modules/dompurify/package.json", "utf8")).version);
  expect(adapter.default).not.toBe(shared);
});

it("keeps hooks and configuration separate from the shared sanitizer", () => {
  adapter.addHook("afterSanitizeAttributes", node => node.removeAttribute("title"));
  expect(adapter.sanitize('<b title="owned">safe</b>')).toBe('<b>safe</b>');
  expect(shared.sanitize('<b title="owned">safe</b>')).toBe('<b title="owned">safe</b>');
  adapter.setConfig({ ALLOWED_TAGS: ["em"] });
  expect(adapter.sanitize('<b>bold</b><em>safe</em>')).toBe('bold<em>safe</em>');
  expect(shared.sanitize('<b>bold</b>')).toBe('<b>bold</b>');
});

it("removes actual hostile markup without losing normal emphasis", () => {
  expect(adapter.sanitize('<img src=x onerror="window.owned++"><script>bad()</script><strong>paper</strong>'))
    .toBe('<img src="x"><strong>paper</strong>');
});

it("redirects only the exact installed vendor module, never foreign lookalikes", async () => {
  const root = process.cwd();
  const vendor = realpathSync("node_modules/monaco-editor/esm/vs/base/browser/dompurify/dompurify.js");
  const plugin = monacoSanitizerBoundary(root);
  const hook = plugin.resolveId as (source: string, importer?: string) => Promise<string | null>;
  const importer = resolve(vendor, "../../dom.js");
  expect(await hook("./dompurify/dompurify.js", importer)).toBe(resolve(root, "static/shared/ts/utils/monaco-sanitizer.ts"));
  expect(await hook(vendor, importer)).toBe(resolve(root, "static/shared/ts/utils/monaco-sanitizer.ts"));
  expect(await hook("./other/dompurify.js", importer)).toBeNull();
  expect(await hook("dompurify", importer)).toBeNull();
  expect(await hook(realpathSync("node_modules/dompurify/dist/purify.es.mjs"), importer)).toBeNull();
  expect(await hook(vendor)).toBeNull();
});
