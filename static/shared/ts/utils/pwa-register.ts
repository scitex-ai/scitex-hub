/**
 * PWA Service Worker Registration
 *
 * Registers the service worker for standalone (app-like) mode on iOS/Android.
 * Users can "Add to Home Screen" to launch without browser chrome.
 */

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
