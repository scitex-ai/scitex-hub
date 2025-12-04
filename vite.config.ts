import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
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

        // Project app
        'project_app/clone_button': resolve(__dirname, 'apps/project_app/static/project_app/ts/clone_button.ts'),
        'project_app/create_project_type': resolve(__dirname, 'apps/project_app/static/project_app/ts/create_project_type.ts'),
        'project_app/init-git-gutter': resolve(__dirname, 'apps/project_app/static/project_app/ts/init-git-gutter.ts'),

        // Scholar app
        'scholar_app/scholar-config': resolve(__dirname, 'apps/scholar_app/static/scholar_app/ts/scholar-config.ts'),

        // Public app
        'public_app/visitor-status': resolve(__dirname, 'apps/public_app/static/public_app/ts/visitor-status.ts'),
        'public_app/server-status': resolve(__dirname, 'apps/public_app/static/public_app/ts/server-status.ts'),
        'public_app/landing-demos-inline': resolve(__dirname, 'apps/public_app/static/public_app/ts/landing-demos-inline.ts'),

        // Accounts app
        'accounts_app/profile': resolve(__dirname, 'apps/accounts_app/static/accounts_app/ts/profile.ts'),
        'accounts_app/account-settings': resolve(__dirname, 'apps/accounts_app/static/accounts_app/ts/account-settings.ts'),
        'accounts_app/ssh_keys': resolve(__dirname, 'apps/accounts_app/static/accounts_app/ts/ssh_keys.ts'),
        'accounts_app/remote_credentials': resolve(__dirname, 'apps/accounts_app/static/accounts_app/ts/remote_credentials.ts'),

        // Social app
        'social_app/explore-inline': resolve(__dirname, 'apps/social_app/static/social_app/ts/explore-inline.ts'),
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
