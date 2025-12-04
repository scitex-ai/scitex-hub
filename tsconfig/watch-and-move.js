#!/usr/bin/env node
/**
 * Watch mode companion - monitors .tsbuild and moves files on change
 *
 * Works alongside `tsc --watch` to automatically move compiled files
 * from ts/ to js/ directories in real-time.
 *
 * Architecture:
 *   tsc outputs to .tsbuild/ maintaining directory structure
 *   This script watches .tsbuild/ and copies files to js/ directories
 *
 * More robust than before:
 *   - Polls for changes (works on all filesystems including Docker volumes)
 *   - Processes files continuously, not just on fs.watch events
 *   - Graceful error handling
 */

const fs = require('fs');
const path = require('path');

const buildDir = path.join(__dirname, '..', '.tsbuild');
const targetDir = path.join(__dirname, '..');

console.log('================================================');
console.log(' TypeScript Watch-and-Move - File Mover Active');
console.log('================================================');
console.log(`   Build dir:  ${buildDir}`);
console.log(`   Target dir: ${targetDir}`);
console.log('');

// Track file modification times to detect changes
const fileModTimes = new Map();

/**
 * Move file from build dir to target dir, converting ts/ to js/
 */
function moveFile(srcPath) {
    const relativePath = path.relative(buildDir, srcPath);
    const targetPath = path.join(targetDir, relativePath.replace(/\/ts\//g, '/js/'));

    // Ensure target directory exists
    const targetDirPath = path.dirname(targetPath);
    try {
        if (!fs.existsSync(targetDirPath)) {
            fs.mkdirSync(targetDirPath, { recursive: true });
        }

        // Copy file
        fs.copyFileSync(srcPath, targetPath);
        return true;
    } catch (err) {
        console.error(`  [ERROR] Failed to move ${relativePath}: ${err.message}`);
        return false;
    }
}

/**
 * Recursively walk directory and find all JS/map/d.ts files
 */
function walkDir(dir, callback) {
    if (!fs.existsSync(dir)) return;

    try {
        const files = fs.readdirSync(dir);
        for (const file of files) {
            const filePath = path.join(dir, file);
            try {
                const stat = fs.statSync(filePath);
                if (stat.isDirectory()) {
                    walkDir(filePath, callback);
                } else if (/\.(js|js\.map|d\.ts|d\.ts\.map)$/.test(file) && filePath.includes('/ts/')) {
                    callback(filePath, stat);
                }
            } catch (e) {
                // File may have been deleted during iteration
            }
        }
    } catch (e) {
        // Directory may have been deleted during iteration
    }
}

/**
 * Process all files - check for new/modified files and move them
 */
function processFiles() {
    let movedCount = 0;
    let newCount = 0;

    walkDir(buildDir, (filePath, stat) => {
        const mtime = stat.mtimeMs;
        const prevMtime = fileModTimes.get(filePath);

        // File is new or modified
        if (prevMtime === undefined) {
            if (moveFile(filePath)) {
                newCount++;
                fileModTimes.set(filePath, mtime);
            }
        } else if (mtime > prevMtime) {
            if (moveFile(filePath)) {
                movedCount++;
                fileModTimes.set(filePath, mtime);
            }
        }
    });

    if (newCount > 0 || movedCount > 0) {
        const timestamp = new Date().toLocaleTimeString();
        console.log(`[${timestamp}] Moved: ${newCount} new, ${movedCount} updated`);
    }

    return newCount + movedCount;
}

// Ensure build directory exists
if (!fs.existsSync(buildDir)) {
    fs.mkdirSync(buildDir, { recursive: true });
    console.log('[INFO] Created .tsbuild directory');
}

// Initial processing after a short delay (let tsc start first)
console.log('[INFO] Waiting for initial compilation...');
setTimeout(() => {
    console.log('[INFO] Processing initial files...');
    const count = processFiles();
    console.log(`[INFO] Initial processing complete: ${count} files`);
    console.log('[INFO] Now polling for changes every 1 second...');
    console.log('');
}, 3000);

// Poll for changes every second (more reliable than fs.watch on Docker volumes)
setInterval(() => {
    processFiles();
}, 1000);

// Also use fs.watch as a backup (may trigger faster on some systems)
try {
    fs.watch(buildDir, { recursive: true }, (eventType, filename) => {
        if (filename && /\.(js|js\.map|d\.ts|d\.ts\.map)$/.test(filename)) {
            // Debounce - processFiles will catch it on next poll
        }
    });
} catch (e) {
    console.log('[WARN] fs.watch not available, using polling only');
}

// Keep process alive and handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n[INFO] Stopping watch-and-move...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n[INFO] Stopping watch-and-move...');
    process.exit(0);
});

// Prevent crash on uncaught errors
process.on('uncaughtException', (err) => {
    console.error('[ERROR] Uncaught exception:', err.message);
    // Don't exit - keep running
});

console.log('[INFO] Watch-and-move started. Press Ctrl+C to stop.');
