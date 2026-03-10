/**
 * Plotly CDN Loader
 *
 * Loads Plotly from CDN while preserving AMD module system compatibility.
 * This prevents conflicts with RequireJS/AMD if present on the page.
 *
 * @module init/plotly-init
 */

(function () {
  const _d = (window as any).define;
  const _r = (window as any).require;
  (window as any).define = undefined;
  (window as any).require = undefined;
  const s = document.createElement("script");
  s.src = "https://cdn.plot.ly/plotly-2.27.0.min.js";
  s.charset = "utf-8";
  s.onload = function () {
    (window as any).define = _d;
    (window as any).require = _r;
  };
  document.head.appendChild(s);
})();
