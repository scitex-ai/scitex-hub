/**
 * Scholar Library - Entry Point
 */

import { initLibraryManager } from "./_library-manager";

console.log("[Library Init] Module loaded, readyState:", document.readyState);

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    console.log("[Library Init] DOMContentLoaded fired, initializing");
    initLibraryManager();
  });
} else {
  console.log("[Library Init] DOM already ready, initializing immediately");
  initLibraryManager();
}
