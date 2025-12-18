import { defineConfig, Plugin } from 'vite';
import { resolve } from 'path';
import * as fs from 'fs';

/**
 * Plugin to resolve /static/ absolute paths to actual file locations
 */
function resolveStaticPaths(): Plugin {
  return {
    name: 'resolve-static-paths',
    enforce: 'pre',
    resolveId(source) {
      // Skip node_modules and external URLs
      if (source.includes('node_modules') || source.startsWith('http')) return null;

      // Handle absolute paths starting with /static/
      if (source.startsWith('/static/')) {
        // Map /static/ to project root static/ directory
        const mappedPath = source.replace('/static/', 'static/');
        const fullPath = resolve(__dirname, mappedPath);
        if (fs.existsSync(fullPath)) {
          return fullPath;
        }
        // Map /static/{app_name}/ to apps/{app_name}/static/{app_name}/
        const match = source.match(/^\/static\/(\w+_app)\/(.*)/);
        if (match) {
          const [, appName, rest] = match;
          const appPath = `apps/${appName}/static/${appName}/${rest}`;
          const appFullPath = resolve(__dirname, appPath);
          if (fs.existsSync(appFullPath)) {
            return appFullPath;
          }
        }
      }

      return null;
    },
  };
}

export default defineConfig({
  // Plugin to resolve /static/ absolute paths
  plugins: [resolveStaticPaths()],

  // Base public path
  base: '/',

  // Root directory - serve files from project root
  root: '.',

  // Public directory (static assets not processed by Vite)
  publicDir: false,

  resolve: {
    alias: {
      '@': resolve(__dirname, 'static/shared/ts'),
      '@types': resolve(__dirname, 'static/shared/ts/types'),
      '@utils': resolve(__dirname, 'static/shared/ts/utils'),
    },
    // Resolve .js imports to .ts files for proper HMR
    extensions: ['.ts', '.js', '.tsx', '.jsx', '.json'],
  },

  // Suppress sourcemap warnings for pre-compiled JS files
  logLevel: 'warn',

  server: {
    // Vite dev server port
    port: 5173,

    // Allow connections from Docker/WSL
    host: '0.0.0.0',

    // Strict port - fail if 5173 is taken
    strictPort: true,

    // Enable HMR with specific settings for Docker/WSL
    hmr: {
      port: 5173,
      host: '127.0.0.1',
    },

    // CORS for Django requests
    cors: true,

    // Watch TypeScript files - use polling for Docker
    watch: {
      usePolling: true,
      interval: 1000, // Check every 1 second (reduce CPU)
    },

    // Allow serving files from project root
    fs: {
      allow: ['.'],
    },

    // Warm up frequently used files
    warmup: {
      clientFiles: [
        'apps/code_app/static/code_app/ts/workspace.ts',
        'apps/code_app/static/code_app/ts/workspace/**/*.ts',
      ],
    },
  },

  build: {
    // Output directory for production build
    outDir: 'staticfiles/vite',

    // Generate manifest for Django integration
    manifest: true,

    rollupOptions: {
      input: {
        // Code app
        'code_app/workspace': resolve(__dirname, 'apps/code_app/static/code_app/ts/workspace.ts'),

        // Vis app
        'vis_app/vis-editor': resolve(__dirname, 'apps/vis_app/static/vis_app/ts/vis-editor.ts'),
        'vis_app/editor-inline': resolve(__dirname, 'apps/vis_app/static/vis_app/ts/editor-inline.ts'),

        // Writer app
        'writer_app/index': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/index.ts'),
        'writer_app/collaboration-panel': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/collaboration-panel.ts'),
        'writer_app/arxiv/submission': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/arxiv/submission.ts'),
        'writer_app/collaboration/session': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/collaboration/session.ts'),
        'writer_app/version_control/index': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/version_control/index.ts'),
        'writer_app/compilation/compilation': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/compilation/compilation.ts'),
        'writer_app/shared/utils': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/shared/utils.ts'),
        'writer_app/editor/preview-panel/index': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/editor/preview-panel/index.ts'),
        'writer_app/editor/collaborative/index': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/editor/collaborative/index.ts'),
        'writer_app/modules/ai2-prompt': resolve(__dirname, 'apps/writer_app/static/writer_app/ts/modules/ai2-prompt.ts'),

        // Project app
        'project_app/clone_button': resolve(__dirname, 'apps/project_app/static/project_app/ts/clone_button.ts'),
        'project_app/create_project_type': resolve(__dirname, 'apps/project_app/static/project_app/ts/create_project_type.ts'),
        'project_app/init-git-gutter': resolve(__dirname, 'apps/project_app/static/project_app/ts/init-git-gutter.ts'),

        // Shared components
        'shared/workspace-panel-resizer': resolve(__dirname, 'static/shared/ts/components/workspace-panel-resizer.ts'),

        // Scholar app
        'scholar_app/scholar-config': resolve(__dirname, 'apps/scholar_app/static/scholar_app/ts/scholar-config.ts'),

        // Public app
        'public_app/visitor-status': resolve(__dirname, 'apps/public_app/static/public_app/ts/visitor-status.ts'),
        'public_app/server-status': resolve(__dirname, 'apps/public_app/static/public_app/ts/server-status.ts'),
        'public_app/landing-demos-inline': resolve(__dirname, 'apps/public_app/static/public_app/ts/landing-demos-inline.ts'),
        'public_app/landing/module-cards': resolve(__dirname, 'apps/public_app/static/public_app/ts/landing/module-cards.ts'),
        'public_app/tools/plot-viewer/index': resolve(__dirname, 'apps/public_app/static/public_app/ts/tools/plot-viewer/index.ts'),
        'public_app/tools/image-viewer': resolve(__dirname, 'apps/public_app/static/public_app/ts/tools/image-viewer.ts'),
        'public_app/pages/api-docs': resolve(__dirname, 'apps/public_app/static/public_app/ts/pages/api-docs.ts'),
        'public_app/pages/release-timeline': resolve(__dirname, 'apps/public_app/static/public_app/ts/pages/release-timeline.ts'),

        // Accounts app
        'accounts_app/profile': resolve(__dirname, 'apps/accounts_app/static/accounts_app/ts/profile.ts'),
        'accounts_app/account-settings': resolve(__dirname, 'apps/accounts_app/static/accounts_app/ts/account-settings.ts'),
        'accounts_app/ssh_keys': resolve(__dirname, 'apps/accounts_app/static/accounts_app/ts/ssh_keys.ts'),
        'accounts_app/remote_credentials': resolve(__dirname, 'apps/accounts_app/static/accounts_app/ts/remote_credentials.ts'),

        // Social app
        'social_app/explore-inline': resolve(__dirname, 'apps/social_app/static/social_app/ts/explore-inline.ts'),

        // Scholar app - additional
        'scholar_app/scholar-workspace-init': resolve(__dirname, 'apps/scholar_app/static/scholar_app/ts/scholar-workspace-init.ts'),
        'scholar_app/bibtex/status-tiles': resolve(__dirname, 'apps/scholar_app/static/scholar_app/ts/bibtex/status-tiles.ts'),
        'scholar_app/graph/citation-graph': resolve(__dirname, 'apps/scholar_app/static/scholar_app/ts/graph/citation-graph.ts'),
        'scholar_app/search/search-controls': resolve(__dirname, 'apps/scholar_app/static/scholar_app/ts/search/search-controls.ts'),
        'scholar_app/search/scitex-search': resolve(__dirname, 'apps/scholar_app/static/scholar_app/ts/search/scitex-search.ts'),

        // Project app - additional
        'project_app/projects/settings': resolve(__dirname, 'apps/project_app/static/project_app/ts/projects/settings.ts'),
        'project_app/shared/project_app': resolve(__dirname, 'apps/project_app/static/project_app/ts/shared/project_app.ts'),
        'project_app/shared/file-tree': resolve(__dirname, 'apps/project_app/static/project_app/ts/shared/file-tree.ts'),
        'project_app/shared/pdf_viewer': resolve(__dirname, 'apps/project_app/static/project_app/ts/shared/pdf_viewer.ts'),
        'project_app/projects/create': resolve(__dirname, 'apps/project_app/static/project_app/ts/projects/create.ts'),
        'project_app/projects/delete_confirmation': resolve(__dirname, 'apps/project_app/static/project_app/ts/projects/delete_confirmation.ts'),
        'project_app/projects/settings_collaborators': resolve(__dirname, 'apps/project_app/static/project_app/ts/projects/settings_collaborators.ts'),
        'project_app/repository/browse': resolve(__dirname, 'apps/project_app/static/project_app/ts/repository/browse.ts'),
        'project_app/repository/browse_toolbar': resolve(__dirname, 'apps/project_app/static/project_app/ts/repository/browse_toolbar.ts'),
        'project_app/repository/colorful-icons': resolve(__dirname, 'apps/project_app/static/project_app/ts/repository/colorful-icons.ts'),
        'project_app/repository/file_browser_git_status': resolve(__dirname, 'apps/project_app/static/project_app/ts/repository/file_browser_git_status.ts'),
        'project_app/repository/file_view': resolve(__dirname, 'apps/project_app/static/project_app/ts/repository/file_view.ts'),
        'project_app/repository/file_edit': resolve(__dirname, 'apps/project_app/static/project_app/ts/repository/file_edit.ts'),
        'project_app/repository/file_history': resolve(__dirname, 'apps/project_app/static/project_app/ts/repository/file_history.ts'),
        'project_app/repository/admin/index': resolve(__dirname, 'apps/project_app/static/project_app/ts/repository/admin/index.ts'),
        'project_app/components/DiffMerge/index': resolve(__dirname, 'apps/project_app/static/project_app/ts/components/DiffMerge/index.ts'),
        'project_app/issues/detail': resolve(__dirname, 'apps/project_app/static/project_app/ts/issues/detail.ts'),
        'project_app/projects/detail': resolve(__dirname, 'apps/project_app/static/project_app/ts/projects/detail.ts'),
        'project_app/pull_requests/conversation': resolve(__dirname, 'apps/project_app/static/project_app/ts/pull_requests/conversation.ts'),
        'project_app/pull_requests/detail': resolve(__dirname, 'apps/project_app/static/project_app/ts/pull_requests/detail.ts'),
        'project_app/pull_requests/form': resolve(__dirname, 'apps/project_app/static/project_app/ts/pull_requests/form.ts'),
        'project_app/security/scan': resolve(__dirname, 'apps/project_app/static/project_app/ts/security/scan.ts'),
        'project_app/security/alert_detail': resolve(__dirname, 'apps/project_app/static/project_app/ts/security/alert_detail.ts'),
        'project_app/users/profile': resolve(__dirname, 'apps/project_app/static/project_app/ts/users/profile.ts'),
        'project_app/workflows/detail': resolve(__dirname, 'apps/project_app/static/project_app/ts/workflows/detail.ts'),
        'project_app/workflows/editor': resolve(__dirname, 'apps/project_app/static/project_app/ts/workflows/editor.ts'),
        'project_app/workflows/run_detail': resolve(__dirname, 'apps/project_app/static/project_app/ts/workflows/run_detail.ts'),

        // Shared utilities (global)
        'shared/utils/theme-switcher': resolve(__dirname, 'static/shared/ts/utils/theme-switcher.ts'),
        'shared/utils/tooltip-auto-position': resolve(__dirname, 'static/shared/ts/utils/tooltip-auto-position.ts'),
        'shared/utils/main': resolve(__dirname, 'static/shared/ts/utils/main.ts'),
        'shared/utils/dropdown': resolve(__dirname, 'static/shared/ts/utils/dropdown.ts'),
        'shared/utils/django-messages': resolve(__dirname, 'static/shared/ts/utils/django-messages.ts'),
        'shared/utils/element-inspector': resolve(__dirname, 'static/shared/ts/utils/element-inspector.ts'),
        'shared/utils/console-interceptor': resolve(__dirname, 'static/shared/ts/utils/console-interceptor.ts'),
        'shared/code-blocks': resolve(__dirname, 'static/shared/ts/code-blocks.ts'),
        'shared/components/confirm-modal': resolve(__dirname, 'static/shared/ts/components/confirm-modal.ts'),
        'shared/components/header': resolve(__dirname, 'static/shared/ts/components/header.ts'),
        'shared/components/workspace-files-tree/WorkspaceFilesTree': resolve(__dirname, 'static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree.ts'),
        'shared/monaco/MonacoTheme': resolve(__dirname, 'static/shared/ts/monaco/MonacoTheme.ts'),
        'shared/utils/highlight-js-bibtex': resolve(__dirname, 'static/shared/ts/utils/highlight-js-bibtex.ts'),
      },
      output: {
        entryFileNames: '[name]-[hash].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },

  // Optimize dependencies
  optimizeDeps: {
    include: ['fabric'],
  },
});
