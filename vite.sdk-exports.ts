/** Shared provider-owned npm export mapping for production Vite and Vitest. */
import * as fs from "fs";
import { resolve } from "path";
import { execFileSync } from "child_process";

/**
 * Discover the scitex-sdk npm exports in checkouts or the installed wheel.
 * Same pattern as discoverScitexUiStatic — supports a Docker/CI `.apps/`
 * layout, the standard sibling checkout, and an explicit env override.
 */
export function discoverScitexSdkRoot(projectRoot: string): string | null {
  if (process.env.SCITEX_SDK_ROOT) {
    return process.env.SCITEX_SDK_ROOT;
  }
  const candidates = [
    resolve(projectRoot, ".apps/scitex-sdk/src/scitex_sdk"),
    resolve(projectRoot, "../scitex-sdk/src/scitex_sdk"),
    // Linked worktrees live under .worktrees/<name>/ (three levels up)
    resolve(projectRoot, "../../../scitex-sdk/src/scitex_sdk"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(resolve(candidate, "package.json"))) return candidate;
  }
  // Production installs the SDK wheel; a sibling checkout is optional.
  // Read the installed provider's own npm exports, just as for editable roots.
  try {
    const installed = execFileSync("python3", ["-c",
      "from importlib.util import find_spec; from pathlib import Path; s=find_spec('scitex_sdk'); print(Path(s.origin).parent if s and s.origin else '')",
    ], { encoding: "utf-8", timeout: 5000 }).trim();
    if (installed && fs.existsSync(resolve(installed, "package.json"))) {
      return installed;
    }
  } catch {
    // A missing provider is reported by the normal unresolved-import build gate.
  }
  return null;
}


export function scitexSdkSubpathAliasesFromRoot(sdkRoot: string | null): Record<string, string> {
  if (!sdkRoot) return {};
  try {
    const pkg = JSON.parse(
      fs.readFileSync(resolve(sdkRoot, "package.json"), "utf-8"),
    );
    const exports = pkg.exports ?? {};
    const aliases: Record<string, string> = {};
    for (const [key, target] of Object.entries(exports)) {
      if (typeof target !== "string") continue;
      const sub = key.replace(/^\.\//, "");
      const dest = (target as string).replace(/^\.\//, "");
      if (!sub.endsWith("/*") || !dest.endsWith("/*")) continue;
      // Strip "/*" (not just "*"): @rollup/plugin-alias appends its own "/"
      // when prefix-matching, so a trailing-slash key would never match.
      aliases[`@scitex/sdk/${sub.slice(0, -2)}`] = resolve(
        sdkRoot,
        dest.slice(0, -2),
      );
    }
    return aliases;
  } catch {
    return {};
  }
}
