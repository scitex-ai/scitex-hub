/**
 * Plotly Lazy Loader
 *
 * Exposes window.loadPlotly() as a Promise-based function for on-demand loading.
 * Plotly (~3.5MB) is only fetched when explicitly requested, preventing
 * unnecessary network traffic on pages that may not display charts.
 *
 * @module init/plotly-lazy
 */

declare global {
  interface Window {
    loadPlotly: () => Promise<typeof Plotly>;
    _plotlyLoading: Promise<typeof Plotly> | undefined;
  }
}

window.loadPlotly = function (): Promise<typeof Plotly> {
  return new Promise(function (resolve, reject) {
    if (typeof Plotly !== "undefined") {
      resolve(Plotly);
      return;
    }
    if (window._plotlyLoading) {
      window._plotlyLoading.then(resolve, reject);
      return;
    }
    window._plotlyLoading = new Promise<typeof Plotly>(function (res, rej) {
      const s = document.createElement("script");
      s.src = "https://cdn.plot.ly/plotly-2.27.0.min.js";
      s.charset = "utf-8";
      s.onload = function () {
        res(Plotly);
      };
      s.onerror = function () {
        rej(new Error("Failed to load Plotly.js"));
      };
      document.head.appendChild(s);
    });
    window._plotlyLoading.then(resolve, reject);
  });
};
