/** Locate the one SDK-owned frontend tree for checkout and wheel consumers. */
import { execFileSync } from "child_process";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";

export interface SdkFrontend {
  packageDir: string;
  uiStatic: string;
}

function fromPackage(packageDir: string): SdkFrontend | null {
  const manifest = resolve(packageDir, "package.json");
  const uiStatic = resolve(packageDir, "ui/static/scitex_sdk/ui");
  if (!existsSync(manifest) || !existsSync(uiStatic)) return null;
  try {
    if (JSON.parse(readFileSync(manifest, "utf-8")).name !== "@scitex/sdk")
      return null;
  } catch {
    return null;
  }
  return { packageDir: resolve(packageDir), uiStatic };
}

export function discoverSdkFrontend(rootDir: string): SdkFrontend | null {
  // Preserve the trusted build override, accepting only the SDK-owned layout.
  if (process.env.SCITEX_UI_STATIC) {
    const frontend = fromPackage(
      resolve(process.env.SCITEX_UI_STATIC, "../../../.."),
    );
    if (frontend?.uiStatic !== resolve(process.env.SCITEX_UI_STATIC))
      throw new Error("SCITEX_UI_STATIC must point to SDK-owned UI assets");
    return frontend;
  }
  try {
    const packageDir = execFileSync(
      "python3",
      [
        "-c",
        "import scitex_sdk; print(scitex_sdk.get_frontend_package_dir())",
      ],
      { encoding: "utf-8", timeout: 5000 },
    ).trim();
    const frontend = fromPackage(packageDir);
    if (frontend) return frontend;
  } catch {
    // A source checkout may be available before the Python environment is set up.
  }
  for (const relative of [
    ".apps/scitex-sdk/src/scitex_sdk",
    "../scitex-sdk/src/scitex_sdk",
  ]) {
    const frontend = fromPackage(resolve(rootDir, relative));
    if (frontend) return frontend;
  }
  return null;
}

/** Transitional names for uncutover legacy JS consumers; no peer code is used. */
export function legacyUiAliases(frontend: SdkFrontend): Record<string, string> {
  return {
    "@scitex/ui/src/scitex_ui/static/scitex_ui": frontend.uiStatic,
    "scitex-ui": frontend.uiStatic,
    "../../../scitex_sdk/ui/css": resolve(frontend.uiStatic, "css"),
  };
}
