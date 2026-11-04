import { afterEach, expect, test } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { discoverScitexSdkRoot, scitexSdkSubpathAliasesFromRoot } from "../../vite.sdk-exports";

const roots: string[] = [];
afterEach(() => { roots.forEach(root => rmSync(root, { recursive: true, force: true })); roots.length = 0; });

test("SDK exports, not a broad prefix guess, own frontend aliases", () => {
  const root = mkdtempSync(join(tmpdir(), "hub-sdk-exports-")); roots.push(root);
  writeFileSync(join(root, "package.json"), JSON.stringify({ exports: {
    "./ui/ts/*": "./ui/static/scitex_sdk/ui/ts/*",
    "./app/*": "./app/static/scitex_sdk/app/*",
    ".": "./index.js",
  }}));
  expect(scitexSdkSubpathAliasesFromRoot(root)).toEqual({
    "@scitex/sdk/ui/ts": join(root, "ui/static/scitex_sdk/ui/ts"),
    "@scitex/sdk/app": join(root, "app/static/scitex_sdk/app"),
  });
});

test("explicit admitted SDK root takes precedence over an unrelated sibling", () => {
  const root = mkdtempSync(join(tmpdir(), "hub-sdk-exports-")); roots.push(root);
  mkdirSync(join(root, ".apps/scitex-sdk/src/scitex_sdk"), { recursive: true });
  writeFileSync(join(root, ".apps/scitex-sdk/src/scitex_sdk/package.json"), "{}");
  const previous = process.env.SCITEX_SDK_ROOT;
  process.env.SCITEX_SDK_ROOT = join(root, "admitted-wheel");
  try { expect(discoverScitexSdkRoot(root)).toBe(join(root, "admitted-wheel")); }
  finally {
    if (previous === undefined) delete process.env.SCITEX_SDK_ROOT;
    else process.env.SCITEX_SDK_ROOT = previous;
  }
});

test("absent or malformed provider exports cannot invent module aliases", () => {
  const root = mkdtempSync(join(tmpdir(), "hub-sdk-exports-")); roots.push(root);
  writeFileSync(join(root, "package.json"), "not JSON");
  expect([scitexSdkSubpathAliasesFromRoot(null), scitexSdkSubpathAliasesFromRoot(root)]).toEqual([{}, {}]);
});
