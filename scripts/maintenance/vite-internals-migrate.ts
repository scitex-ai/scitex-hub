#!/usr/bin/env npx tsx
/**
 * Migration: Rename internal TS files/dirs with _ prefix for Vite auto-discovery.
 * Usage: npx tsx scripts/maintenance/vite-internals-migrate.ts [--dry-run]
 */
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import {
  DIR_RENAMES,
  FILE_RENAMES,
  TS_SEARCH_DIRS,
} from "./vite-internals-data";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "../..");
const DRY_RUN = process.argv.includes("--dry-run");

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function collectTsFiles(dir: string): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, item.name);
    if (item.isDirectory()) {
      results.push(...collectTsFiles(full));
    } else if (item.name.endsWith(".ts")) {
      results.push(full);
    }
  }
  return results;
}

/** Update import paths for a directory rename (only match /oldSeg/ with trailing slash) */
function updateDirImports(
  filePath: string,
  oldSeg: string,
  newSeg: string,
): boolean {
  const content = fs.readFileSync(filePath, "utf-8");
  const escaped = escapeRegex(oldSeg);
  // Only match when followed by / (directory traversal), not at end of import
  const re = new RegExp(
    `(["'\`](?:\\./|\\.\\./)(?:[^"'\`]*/)?)${escaped}/`,
    "g",
  );
  const updated = content.replace(re, `$1${newSeg}/`);
  if (updated !== content) {
    if (!DRY_RUN) fs.writeFileSync(filePath, updated, "utf-8");
    return true;
  }
  return false;
}

/** Update import paths for a file rename (match /oldSeg at end of import or before /) */
function updateFileImports(
  filePath: string,
  oldSeg: string,
  newSeg: string,
): boolean {
  const content = fs.readFileSync(filePath, "utf-8");
  const escaped = escapeRegex(oldSeg);
  const re = new RegExp(
    `(["'\`](?:\\./|\\.\\./)(?:[^"'\`]*/)?)${escaped}([/"'\`])`,
    "g",
  );
  const updated = content.replace(re, `$1${newSeg}$2`);
  if (updated !== content) {
    if (!DRY_RUN) fs.writeFileSync(filePath, updated, "utf-8");
    return true;
  }
  return false;
}

// ── Main ─────────────────────────────────────────────────────
console.log(DRY_RUN ? "=== DRY RUN ===" : "=== EXECUTING ===");

let dirCount = 0,
  fileCount = 0,
  importCount = 0;

// Step 1: Directory renames
console.log("\n── Directory renames ──");
for (const [parentDir, oldName, newName] of DIR_RENAMES) {
  const oldPath = path.join(ROOT, parentDir, oldName);
  const newPath = path.join(ROOT, parentDir, newName);
  if (!fs.existsSync(oldPath)) {
    console.log(`  SKIP: ${parentDir}/${oldName}`);
    continue;
  }
  if (fs.existsSync(newPath)) {
    console.log(`  EXISTS: ${parentDir}/${newName}`);
    continue;
  }
  console.log(`  ${parentDir}/${oldName} → ${newName}`);
  if (!DRY_RUN) fs.renameSync(oldPath, newPath);
  dirCount++;
}

// Step 2: File renames
console.log("\n── File renames ──");
for (const [dir, oldName, newName] of FILE_RENAMES) {
  const oldPath = path.join(ROOT, dir, oldName);
  const newPath = path.join(ROOT, dir, newName);
  if (!fs.existsSync(oldPath)) {
    console.log(`  SKIP: ${dir}/${oldName}`);
    continue;
  }
  console.log(`  ${dir}/${oldName} → ${newName}`);
  if (!DRY_RUN) fs.renameSync(oldPath, newPath);
  fileCount++;
}

// Step 3: Update imports
console.log("\n── Import updates ──");
const allTs: string[] = [];
for (const d of TS_SEARCH_DIRS)
  allTs.push(...collectTsFiles(path.join(ROOT, d)));
console.log(`  Scanning ${allTs.length} files...`);

const dirOps = DIR_RENAMES.map(([, o, n]) => [o, n] as [string, string]);
const fileOps = FILE_RENAMES.map(
  ([, o, n]) =>
    [o.replace(".ts", ""), n.replace(".ts", "")] as [string, string],
);

for (const f of allTs) {
  let changed = false;
  for (const [o, n] of dirOps) {
    if (updateDirImports(f, o, n)) changed = true;
  }
  for (const [o, n] of fileOps) {
    if (updateFileImports(f, o, n)) changed = true;
  }
  if (changed) {
    importCount++;
    if (DRY_RUN) console.log(`  Would update: ${path.relative(ROOT, f)}`);
  }
}

console.log(`\n── Summary ──`);
console.log(
  `  Dirs: ${dirCount}, Files: ${fileCount}, Imports updated: ${importCount}`,
);
if (DRY_RUN) console.log("  (no changes made)");
