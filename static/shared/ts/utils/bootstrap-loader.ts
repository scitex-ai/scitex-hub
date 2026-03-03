/**
 * Bootstrap 5 loader — wrapped to prevent AMD conflicts with Monaco Editor's
 * RequireJS loader. Temporarily disables AMD define/require while Bootstrap loads.
 *
 * Extracted from global_body_scripts.html inline <script>.
 */

(function () {
  // Temporarily disable AMD define to prevent Bootstrap from registering as AMD module
  const originalDefine = (window as any).define;
  const originalRequire = (window as any).require;
  (window as any).define = undefined;
  (window as any).require = undefined;

  // Load Bootstrap
  const script = document.createElement("script");
  script.src =
    "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js";
  script.integrity =
    "sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HAuoJl+0I4"; // pragma: allowlist secret
  script.crossOrigin = "anonymous";
  script.onload = () => {
    // Restore AMD after Bootstrap loads
    (window as any).define = originalDefine;
    (window as any).require = originalRequire;
    console.log("[Bootstrap] Loaded successfully without AMD conflicts");
  };
  document.head.appendChild(script);
})();
