/**
 * Monaco Editor Loader
 * Loads Monaco from CDN if not already available.
 * Handles deduplication with console-mode's Monaco loader.
 */

const MONACO_CDN =
  "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs";
const LOADER_URL = `${MONACO_CDN}/loader.min.js`;

let loadPromise: Promise<boolean> | null = null;

/** Load Monaco editor, returning true if available. */
export function loadMonaco(): Promise<boolean> {
  if ((window as any).monaco) return Promise.resolve(true);
  if (loadPromise) return loadPromise;

  loadPromise = new Promise<boolean>((resolve) => {
    // If already loading elsewhere, wait for the ready event
    if ((window as any).require?.config) {
      (window as any).require(["vs/editor/editor.main"], () => {
        (window as any).monacoReady = true;
        window.dispatchEvent(new Event("monaco-ready"));
        resolve(true);
      });
      return;
    }

    // Listen for monaco-ready from other loaders (e.g. console-mode)
    const readyHandler = () => {
      resolve(!!(window as any).monaco);
    };
    window.addEventListener("monaco-ready", readyHandler, { once: true });

    // Load the AMD loader script
    const script = document.createElement("script");
    script.src = LOADER_URL;
    script.onload = () => {
      const req = (window as any).require;
      if (!req) {
        resolve(false);
        return;
      }
      req.config({ paths: { vs: MONACO_CDN } });
      req(["vs/editor/editor.main"], () => {
        window.removeEventListener("monaco-ready", readyHandler);
        (window as any).monacoReady = true;
        window.dispatchEvent(new Event("monaco-ready"));
        resolve(true);
      });
    };
    script.onerror = () => resolve(false);

    // Poll fallback — another loader (writer, console) may set window.monaco
    const poll = setInterval(() => {
      if ((window as any).monaco) {
        clearInterval(poll);
        window.removeEventListener("monaco-ready", readyHandler);
        resolve(true);
      }
    }, 200);
    setTimeout(() => clearInterval(poll), 10000);

    document.head.appendChild(script);
  });

  return loadPromise;
}
