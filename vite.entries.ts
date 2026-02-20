/**
 * Vite build entry points - extracted from vite.config.ts
 * Each key maps to a TypeScript source file for bundling
 */
import { resolve } from "path";
import * as fs from "fs";

/**
 * Generate entry points from directory
 * Usage: generateEntries("apps/scholar_app/static/scholar_app/ts/search", "scholar_app/search")
 */
export function generateEntries(
  rootDir: string,
  dir: string,
  prefix: string,
): Record<string, string> {
  const entries: Record<string, string> = {};
  const fullDir = resolve(rootDir, dir);
  if (fs.existsSync(fullDir)) {
    const files = fs
      .readdirSync(fullDir)
      .filter((f: string) => f.endsWith(".ts") && !f.startsWith("_"));
    for (const file of files) {
      const name = file.replace(".ts", "");
      entries[`${prefix}/${name}`] = resolve(fullDir, file);
    }
  }
  return entries;
}

/** Helper to create resolve paths relative to root */
function r(rootDir: string, path: string): string {
  return resolve(rootDir, path);
}

export function getEntryPoints(rootDir: string): Record<string, string> {
  return {
    // Console app
    "console_app/workspace": r(
      rootDir,
      "apps/console_app/static/console_app/ts/workspace.ts",
    ),

    // Vis app
    "vis_app/vis-editor": r(
      rootDir,
      "apps/vis_app/static/vis_app/ts/vis-editor.ts",
    ),
    "vis_app/editor-inline": r(
      rootDir,
      "apps/vis_app/static/vis_app/ts/editor-inline.ts",
    ),
    "vis_app/vis-panel-toggle": r(
      rootDir,
      "apps/vis_app/static/vis_app/ts/vis-panel-toggle.ts",
    ),

    // Writer app
    "writer_app/index": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/index.ts",
    ),
    "writer_app/collaboration-panel": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/collaboration-panel.ts",
    ),
    "writer_app/arxiv/submission": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/arxiv/submission.ts",
    ),
    "writer_app/collaboration/session": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/collaboration/session.ts",
    ),
    "writer_app/version_control/index": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/version_control/index.ts",
    ),
    "writer_app/compilation/compilation": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/compilation/compilation.ts",
    ),
    "writer_app/shared/utils": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/shared/utils.ts",
    ),
    "writer_app/editor/preview-panel/index": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/editor/preview-panel/index.ts",
    ),
    "writer_app/editor/collaborative/index": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/editor/collaborative/index.ts",
    ),
    "writer_app/modules/ai2-prompt": r(
      rootDir,
      "apps/writer_app/static/writer_app/ts/modules/ai2-prompt.ts",
    ),

    // Project app
    "project_app/clone_button": r(
      rootDir,
      "apps/project_app/static/project_app/ts/clone_button.ts",
    ),
    "project_app/create_project_type": r(
      rootDir,
      "apps/project_app/static/project_app/ts/create_project_type.ts",
    ),
    "project_app/init-git-gutter": r(
      rootDir,
      "apps/project_app/static/project_app/ts/init-git-gutter.ts",
    ),
    "project_app/projects/settings": r(
      rootDir,
      "apps/project_app/static/project_app/ts/projects/settings.ts",
    ),
    "project_app/shared/project_app": r(
      rootDir,
      "apps/project_app/static/project_app/ts/shared/project_app.ts",
    ),
    "project_app/shared/file-tree": r(
      rootDir,
      "apps/project_app/static/project_app/ts/shared/file-tree.ts",
    ),
    "project_app/shared/pdf_viewer": r(
      rootDir,
      "apps/project_app/static/project_app/ts/shared/pdf_viewer.ts",
    ),
    "project_app/projects/create": r(
      rootDir,
      "apps/project_app/static/project_app/ts/projects/create.ts",
    ),
    "project_app/projects/delete_confirmation": r(
      rootDir,
      "apps/project_app/static/project_app/ts/projects/delete_confirmation.ts",
    ),
    "project_app/projects/settings_collaborators": r(
      rootDir,
      "apps/project_app/static/project_app/ts/projects/settings_collaborators.ts",
    ),
    "project_app/repository/browse": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/browse.ts",
    ),
    "project_app/repository/browse_toolbar": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/browse_toolbar.ts",
    ),
    "project_app/repository/colorful-icons": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/colorful-icons.ts",
    ),
    "project_app/repository/file_browser_git_status": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/file_browser_git_status.ts",
    ),
    "project_app/repository/file_table_hidden_sync": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/file_table_hidden_sync.ts",
    ),
    "project_app/repository/file_view": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/file_view.ts",
    ),
    "project_app/repository/file_edit": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/file_edit.ts",
    ),
    "project_app/repository/file_history": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/file_history.ts",
    ),
    "project_app/repository/admin/index": r(
      rootDir,
      "apps/project_app/static/project_app/ts/repository/admin/index.ts",
    ),
    "project_app/components/DiffMerge/index": r(
      rootDir,
      "apps/project_app/static/project_app/ts/components/DiffMerge/index.ts",
    ),
    "project_app/issues/detail": r(
      rootDir,
      "apps/project_app/static/project_app/ts/issues/detail.ts",
    ),
    "project_app/projects/detail": r(
      rootDir,
      "apps/project_app/static/project_app/ts/projects/detail.ts",
    ),
    "project_app/pull_requests/conversation": r(
      rootDir,
      "apps/project_app/static/project_app/ts/pull_requests/conversation.ts",
    ),
    "project_app/pull_requests/detail": r(
      rootDir,
      "apps/project_app/static/project_app/ts/pull_requests/detail.ts",
    ),
    "project_app/pull_requests/form": r(
      rootDir,
      "apps/project_app/static/project_app/ts/pull_requests/form.ts",
    ),
    "project_app/security/scan": r(
      rootDir,
      "apps/project_app/static/project_app/ts/security/scan.ts",
    ),
    "project_app/security/alert_detail": r(
      rootDir,
      "apps/project_app/static/project_app/ts/security/alert_detail.ts",
    ),
    "project_app/users/profile": r(
      rootDir,
      "apps/project_app/static/project_app/ts/users/profile.ts",
    ),
    "project_app/workflows/detail": r(
      rootDir,
      "apps/project_app/static/project_app/ts/workflows/detail.ts",
    ),
    "project_app/workflows/editor": r(
      rootDir,
      "apps/project_app/static/project_app/ts/workflows/editor.ts",
    ),
    "project_app/workflows/run_detail": r(
      rootDir,
      "apps/project_app/static/project_app/ts/workflows/run_detail.ts",
    ),

    // Shared components
    "shared/workspace-panel-resizer": r(
      rootDir,
      "static/shared/ts/components/workspace-panel-resizer.ts",
    ),
    "shared/collapsible-panel-click-expand": r(
      rootDir,
      "static/shared/ts/components/collapsible-panel-click-expand.ts",
    ),
    "shared/utils/theme-switcher": r(
      rootDir,
      "static/shared/ts/utils/theme-switcher.ts",
    ),
    "shared/utils/tooltip-auto-position": r(
      rootDir,
      "static/shared/ts/utils/tooltip-auto-position.ts",
    ),
    "shared/utils/main": r(rootDir, "static/shared/ts/utils/main.ts"),
    "shared/utils/dropdown": r(rootDir, "static/shared/ts/utils/dropdown.ts"),
    "shared/utils/django-messages": r(
      rootDir,
      "static/shared/ts/utils/django-messages.ts",
    ),
    "shared/utils/element-inspector": r(
      rootDir,
      "static/shared/ts/utils/element-inspector.ts",
    ),
    "shared/utils/console-interceptor": r(
      rootDir,
      "static/shared/ts/utils/console-interceptor.ts",
    ),
    "shared/code-blocks": r(rootDir, "static/shared/ts/code-blocks.ts"),
    "shared/components/confirm-modal": r(
      rootDir,
      "static/shared/ts/components/confirm-modal.ts",
    ),
    "shared/components/header": r(
      rootDir,
      "static/shared/ts/components/header.ts",
    ),
    "shared/components/workspace-files-tree/WorkspaceFilesTree": r(
      rootDir,
      "static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree.ts",
    ),
    "shared/monaco/MonacoTheme": r(
      rootDir,
      "static/shared/ts/monaco/MonacoTheme.ts",
    ),
    "shared/utils/highlight-js-bibtex": r(
      rootDir,
      "static/shared/ts/utils/highlight-js-bibtex.ts",
    ),
    "shared/utils/analytics": r(rootDir, "static/shared/ts/utils/analytics.ts"),
    "shared/utils/visitor-heartbeat": r(
      rootDir,
      "static/shared/ts/utils/visitor-heartbeat.ts",
    ),
    "shared/components/product-tour": r(
      rootDir,
      "static/shared/ts/components/product-tour.ts",
    ),
    "shared/components/cookie-consent": r(
      rootDir,
      "static/shared/ts/components/cookie-consent.ts",
    ),
    "shared/components/project-selector": r(
      rootDir,
      "static/shared/ts/components/project-selector.ts",
    ),
    "shared/workspace-tree-init": r(
      rootDir,
      "static/shared/ts/components/workspace-files-tree/auto-init.ts",
    ),
    "shared/global-ai-chat": r(rootDir, "static/shared/ts/global-ai-chat.ts"),
    "shared/module-tab-switcher": r(
      rootDir,
      "static/shared/ts/module-tab-switcher.ts",
    ),
    "shared/module-tab-context-menu": r(
      rootDir,
      "static/shared/ts/components/module-tab-context-menu.ts",
    ),

    // Scholar app
    "scholar_app/scholar-config": r(
      rootDir,
      "apps/scholar_app/static/scholar_app/ts/scholar-config.ts",
    ),
    "scholar_app/scholar-workspace-init": r(
      rootDir,
      "apps/scholar_app/static/scholar_app/ts/scholar-workspace-init.ts",
    ),
    "scholar_app/bibtex/status-tiles": r(
      rootDir,
      "apps/scholar_app/static/scholar_app/ts/bibtex/status-tiles.ts",
    ),
    "scholar_app/graph/citation-graph": r(
      rootDir,
      "apps/scholar_app/static/scholar_app/ts/graph/citation-graph.ts",
    ),
    "scholar_app/library/library-init": r(
      rootDir,
      "apps/scholar_app/static/scholar_app/ts/library/library-init.ts",
    ),
    ...generateEntries(
      rootDir,
      "apps/scholar_app/static/scholar_app/ts/search",
      "scholar_app/search",
    ),

    // Public app
    "public_app/visitor-status": r(
      rootDir,
      "apps/public_app/static/public_app/ts/visitor-status.ts",
    ),
    "public_app/server-status": r(
      rootDir,
      "apps/public_app/static/public_app/ts/server-status.ts",
    ),
    "public_app/landing-demos-inline": r(
      rootDir,
      "apps/public_app/static/public_app/ts/landing-demos-inline.ts",
    ),
    "public_app/landing/module-cards": r(
      rootDir,
      "apps/public_app/static/public_app/ts/landing/module-cards.ts",
    ),
    "public_app/landing/hero-demo": r(
      rootDir,
      "apps/public_app/static/public_app/ts/landing/hero-demo.ts",
    ),
    "public_app/tools/view-plot/index": r(
      rootDir,
      "apps/public_app/static/public_app/ts/tools/view-plot/index.ts",
    ),
    "public_app/tools/view-image": r(
      rootDir,
      "apps/public_app/static/public_app/ts/tools/view-image.ts",
    ),
    "public_app/tools-panel": r(
      rootDir,
      "apps/public_app/static/public_app/ts/tools-panel.ts",
    ),
    "public_app/tools/run-stats": r(
      rootDir,
      "apps/public_app/static/public_app/ts/tools/run-stats/index.ts",
    ),
    "public_app/pages/api-docs": r(
      rootDir,
      "apps/public_app/static/public_app/ts/pages/api-docs.ts",
    ),
    "public_app/pages/release-timeline": r(
      rootDir,
      "apps/public_app/static/public_app/ts/pages/release-timeline.ts",
    ),
    "public_app/pages/visitor-pool-full": r(
      rootDir,
      "apps/public_app/static/public_app/ts/pages/visitor-pool-full.ts",
    ),

    // Accounts app
    "accounts_app/profile": r(
      rootDir,
      "apps/accounts_app/static/accounts_app/ts/profile.ts",
    ),
    "accounts_app/account-settings": r(
      rootDir,
      "apps/accounts_app/static/accounts_app/ts/account-settings.ts",
    ),
    "accounts_app/ssh_keys": r(
      rootDir,
      "apps/accounts_app/static/accounts_app/ts/ssh_keys.ts",
    ),
    "accounts_app/remote_credentials": r(
      rootDir,
      "apps/accounts_app/static/accounts_app/ts/remote_credentials.ts",
    ),
    "accounts_app/ai_providers": r(
      rootDir,
      "apps/accounts_app/static/accounts_app/ts/ai_providers.ts",
    ),

    // Social app
    "social_app/explore-inline": r(
      rootDir,
      "apps/social_app/static/social_app/ts/explore-inline.ts",
    ),

    // Verifier app
    "clew_app/clew-init": r(
      rootDir,
      "apps/clew_app/static/clew_app/ts/clew-init.ts",
    ),

    // Hub app (tree init moved to shared/workspace-tree-init)

    // Workspace shell SPA
    "workspace_app/workspace-shell": r(
      rootDir,
      "static/workspace_app/ts/workspace-shell.ts",
    ),
  };
}
