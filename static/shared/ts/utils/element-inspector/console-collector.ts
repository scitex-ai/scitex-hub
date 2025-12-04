/**
 * Console Collector for Element Inspector
 * Captures console logs and provides debug snapshot functionality
 */

import { NotificationManager } from "./notification-manager.js";

interface ConsoleEntry {
  type: "log" | "warn" | "error" | "info" | "debug";
  timestamp: string;
  args: string[];
  source: string;
}

export class ConsoleCollector {
  private notificationManager: NotificationManager;
  private consoleLogs: ConsoleEntry[] = [];
  private networkErrors: string[] = [];
  private maxLogs: number = 1000;
  private isCapturing: boolean = false;

  // Store original console methods
  private originalConsole: {
    log: typeof console.log;
    warn: typeof console.warn;
    error: typeof console.error;
    info: typeof console.info;
    debug: typeof console.debug;
  };

  constructor(notificationManager: NotificationManager) {
    this.notificationManager = notificationManager;
    this.originalConsole = {
      log: console.log.bind(console),
      warn: console.warn.bind(console),
      error: console.error.bind(console),
      info: console.info.bind(console),
      debug: console.debug.bind(console),
    };

    // Start capturing immediately
    this.startCapturing();
    // Also capture network errors
    this.captureNetworkErrors();
  }

  /**
   * Capture network errors (404s, etc.) using Performance API
   */
  private captureNetworkErrors(): void {
    // Listen for future resource errors
    window.addEventListener("error", (e) => {
      if (e.target && (e.target as HTMLElement).tagName) {
        const target = e.target as HTMLElement;
        const src = (target as any).src || (target as any).href || "";
        if (src) {
          this.networkErrors.push(`Failed to load resource: ${src}`);
        }
      }
    }, true);
  }

  private startCapturing(): void {
    if (this.isCapturing) return;
    this.isCapturing = true;

    const self = this;

    // Override console methods to capture logs
    console.log = function (...args: any[]) {
      self.captureLog("log", args);
      self.originalConsole.log.apply(console, args);
    };

    console.warn = function (...args: any[]) {
      self.captureLog("warn", args);
      self.originalConsole.warn.apply(console, args);
    };

    console.error = function (...args: any[]) {
      self.captureLog("error", args);
      self.originalConsole.error.apply(console, args);
    };

    console.info = function (...args: any[]) {
      self.captureLog("info", args);
      self.originalConsole.info.apply(console, args);
    };

    console.debug = function (...args: any[]) {
      self.captureLog("debug", args);
      self.originalConsole.debug.apply(console, args);
    };
  }

  private captureLog(
    type: "log" | "warn" | "error" | "info" | "debug",
    args: any[],
  ): void {
    const entry: ConsoleEntry = {
      type,
      timestamp: new Date().toISOString(),
      args: args.map((arg) => this.stringify(arg)),
      source: this.getCallSource(),
    };

    this.consoleLogs.push(entry);

    // Keep only the last maxLogs entries
    if (this.consoleLogs.length > this.maxLogs) {
      this.consoleLogs.shift();
    }
  }

  /**
   * Get the source file and line number of the console call
   */
  private getCallSource(): string {
    try {
      const stack = new Error().stack;
      if (!stack) return "";

      const lines = stack.split("\n");
      // Skip: Error, getCallSource, captureLog, console.xxx override, actual caller
      for (let i = 4; i < lines.length; i++) {
        const line = lines[i];
        // Match file:line:col pattern
        const match = line.match(/(?:at\s+)?(?:.*?\s+\()?([^\s()]+):(\d+):(\d+)\)?$/);
        if (match) {
          const [, file, lineNum] = match;
          // Clean up file path - get just filename
          const fileName = file.split("/").pop() || file;
          // Skip internal files
          if (fileName.includes("console-collector")) continue;
          return `${fileName}:${lineNum}`;
        }
      }
    } catch (e) {
      // Ignore errors
    }
    return "";
  }

  private stringify(obj: any): string {
    if (obj === null) return "null";
    if (obj === undefined) return "undefined";
    if (typeof obj === "string") return obj;
    if (typeof obj === "number" || typeof obj === "boolean") return String(obj);
    if (obj instanceof Error) {
      return `${obj.name}: ${obj.message}\n${obj.stack || ""}`;
    }
    try {
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      return String(obj);
    }
  }

  public getConsoleLogs(): string {
    // Try to get logs from the global console interceptor first (captures everything since page load)
    const globalInterceptor = (window as any).__consoleInterceptor;
    if (globalInterceptor && typeof globalInterceptor.getDevToolsFormat === "function") {
      const logs = globalInterceptor.getDevToolsFormat();
      if (logs && logs !== "No console logs captured.") {
        return logs;
      }
    }

    // Fallback to our own captured logs
    const failedResources = this.getFailedResources();
    const totalEntries = this.consoleLogs.length + failedResources.length + this.networkErrors.length;

    if (totalEntries === 0) {
      return "No console logs captured.";
    }

    let output = "";

    // Add failed resources first (these are typically 404 errors)
    if (failedResources.length > 0) {
      failedResources.forEach((resource) => {
        output += `❌ Failed to load resource: the server responded with a status of 404 (Not Found)\n`;
        output += `   ${resource}\n`;
      });
    }

    // Add captured network errors
    if (this.networkErrors.length > 0) {
      this.networkErrors.forEach((error) => {
        output += `❌ ${error}\n`;
      });
    }

    // Add console logs with source info like browser DevTools
    this.consoleLogs.forEach((entry) => {
      const source = entry.source ? `${entry.source} ` : "";
      output += `${source}${entry.args.join(" ")}\n`;
    });

    return output;
  }

  /**
   * Get failed resources from Performance API
   */
  private getFailedResources(): string[] {
    const failed: string[] = [];

    if (window.performance && window.performance.getEntriesByType) {
      const resources = window.performance.getEntriesByType("resource") as PerformanceResourceTiming[];

      // Check for resources with transferSize = 0 and no cache (likely 404)
      // Also check responseStatus if available (newer browsers)
      resources.forEach((r) => {
        // If responseStatus is available and not 2xx/3xx, it's an error
        if ((r as any).responseStatus && (r as any).responseStatus >= 400) {
          failed.push(r.name);
        }
      });
    }

    return failed;
  }

  private getTypeIcon(type: string): string {
    switch (type) {
      case "error":
        return "❌";
      case "warn":
        return "⚠️";
      case "info":
        return "ℹ️";
      case "debug":
        return "🔍";
      default:
        return "📝";
    }
  }

  public async captureDebugSnapshot(): Promise<void> {
    // Generate console logs text
    const textSnapshot = this.generateDebugSnapshot();

    // Show flash
    this.notificationManager.showCameraFlash();
    await new Promise((resolve) => setTimeout(resolve, 150));

    // Capture screenshot
    const screenshotBlob = await this.captureScreenshot();

    // Step 1: Copy screenshot
    let screenshotCopied = false;
    if (screenshotBlob) {
      try {
        await navigator.clipboard.write([
          new ClipboardItem({ "image/png": screenshotBlob }),
        ]);
        screenshotCopied = true;
        this.notificationManager.showNotification("1/3 ✓ Screenshot copied", "success");
      } catch (e) {
        this.notificationManager.showNotification("1/3 ✗ Screenshot failed", "error");
      }
    } else {
      this.notificationManager.showNotification("1/3 ✗ Screenshot failed", "error");
    }

    await new Promise((resolve) => setTimeout(resolve, 500));

    // Step 2: Copy console logs
    let logsCopied = false;
    try {
      await navigator.clipboard.writeText(textSnapshot);
      logsCopied = true;
      this.notificationManager.showNotification("2/3 ✓ Console logs copied", "success");
    } catch (e) {
      this.originalConsole.error("[ConsoleCollector] Failed to copy text:", e);
      this.notificationManager.showNotification("2/3 ✗ Console logs failed", "error");
    }

    await new Promise((resolve) => setTimeout(resolve, 500));

    // Step 3: Final summary
    if (screenshotCopied && logsCopied) {
      this.notificationManager.showNotification("3/3 ✓ Both copied!", "success");
    } else if (logsCopied) {
      this.notificationManager.showNotification("3/3 ✓ Logs only", "success");
    } else if (screenshotCopied) {
      this.notificationManager.showNotification("3/3 ✓ Screenshot only", "success");
    } else {
      this.notificationManager.showNotification("3/3 ✗ Copy failed", "error");
    }

    this.notificationManager.triggerCopyCallback();
  }

  private async captureScreenshot(): Promise<Blob | null> {
    // Use modern-screenshot library which supports oklch colors
    try {
      const domToImage = await this.loadDomToImage();
      if (!domToImage) {
        this.originalConsole.log("[ConsoleCollector] dom-to-image not available");
        return null;
      }

      // Temporarily suppress console.error to hide cross-origin CSS errors from dom-to-image
      const originalError = console.error;
      console.error = (...args: any[]) => {
        const msg = args[0]?.toString() || "";
        // Suppress known dom-to-image cross-origin CSS errors
        if (msg.includes("domtoimage") && msg.includes("CSS rules")) {
          return;
        }
        originalError.apply(console, args);
      };

      try {
        const blob = await domToImage.toBlob(document.documentElement, {
          width: window.innerWidth,
          height: window.innerHeight,
          style: {
            transform: `translate(-${window.scrollX}px, -${window.scrollY}px)`,
          },
          filter: (node: Node) => {
            // Filter out inspector overlay
            if (node instanceof Element && node.id === "element-inspector-overlay") {
              return false;
            }
            return true;
          },
        });

        return blob;
      } finally {
        // Restore console.error
        console.error = originalError;
      }
    } catch (err) {
      this.originalConsole.error("[ConsoleCollector] Screenshot failed:", err);
      return null;
    }
  }

  private loadDomToImage(): Promise<any> {
    return new Promise((resolve) => {
      // Already loaded
      if ((window as any).domtoimage) {
        resolve((window as any).domtoimage);
        return;
      }

      // Load dom-to-image-more from CDN (better modern CSS support)
      const script = document.createElement("script");
      script.src =
        "https://cdnjs.cloudflare.com/ajax/libs/dom-to-image-more/3.3.0/dom-to-image-more.min.js";
      script.onload = () => resolve((window as any).domtoimage);
      script.onerror = () => {
        this.originalConsole.error("[ConsoleCollector] Failed to load dom-to-image");
        resolve(null);
      };
      document.head.appendChild(script);
    });
  }

  private generateDebugSnapshot(): string {
    // Just return the console logs in DevTools format - exactly like F12 console
    return this.getConsoleLogs();
  }

  public clearLogs(): void {
    this.consoleLogs = [];
    this.originalConsole.log("[ConsoleCollector] Logs cleared");
  }
}
