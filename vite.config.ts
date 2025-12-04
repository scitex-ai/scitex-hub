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
