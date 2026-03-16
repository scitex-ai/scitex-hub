/**
 * React Fast Refresh preamble for Django-served pages.
 *
 * Sets up the global hooks synchronously so that @vitejs/plugin-react
 * can detect the preamble when JSX modules load.
 */

// Set preamble globals synchronously — required before any .tsx module loads
(window as any).$RefreshReg$ = () => {};
(window as any).$RefreshSig$ = () => (type: any) => type;
(window as any).__vite_plugin_react_preamble_installed__ = true;

// Load the actual runtime asynchronously for Hot Module Replacement
import(/* @vite-ignore */ "/@react-refresh")
  .then((RefreshRuntime) => {
    RefreshRuntime.default.injectIntoGlobalHook(window);
  })
  .catch(() => {
    // Not in dev mode — ignore
  });
