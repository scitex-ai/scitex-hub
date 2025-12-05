/**
 * project_app.ts - Entry point (Orchestrator Pattern)
 *
 * This file has been refactored from a 1,347-line monolith into a modular architecture.
 * All functionality has been extracted into focused modules under ./project-app/
 *
 * Original: 1,347 lines (5x over 256-line threshold)
 * Refactored: 9 modules (avg 137 lines each) + this 20-line orchestrator
 *
 * Modules:
 * - sidebar-manager.ts (68 lines) - Sidebar initialization and toggling
 * - file-tree-manager.ts (39 lines) - File tree loading and navigation
 * - project-actions.ts (216 lines) - Watch/Star/Fork functionality
 * - project-forms.ts (365 lines) - Create/Settings/Delete forms
 * - file-manager.ts (121 lines) - File upload and operations
 * - directory-ops.ts (205 lines) - Directory copying and operations
 * - user-profile.ts (129 lines) - User profile repository search
 * - utils.ts (94 lines) - Common utility functions
 * - index.ts (65 lines) - Module orchestrator
 *
 * Backup: project_app_monolithic_backup.ts
 */

// Import and re-export everything from the orchestrator
export * from "./project-app/index";

console.log("[DEBUG] project_app.ts entry point loaded (orchestrator pattern)");
