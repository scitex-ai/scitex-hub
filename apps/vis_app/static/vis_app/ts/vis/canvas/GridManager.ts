/**
 * GridManager - Handles grid rendering and visibility
 *
 * Responsibilities:
 * - Draw grid using inline SVG data (light/dark mode)
 * - Toggle grid visibility
 * - Clear grid background
 *
 * PERFORMANCE: Uses inline SVG data URIs to avoid HTTP request issues
 */

// Inline SVG grid definitions (avoids HTTP serving issues with Vite dev server)
const GRID_DARK_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="2126" height="2835">
  <rect width="2126" height="2835" fill="#2a2a2a"/>
  <defs>
    <pattern id="minor-grid" width="11.811023622047244" height="11.811023622047244" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="11.811023622047244" stroke="#505050" stroke-width="0.5"/>
      <line x1="0" y1="0" x2="11.811023622047244" y2="0" stroke="#505050" stroke-width="0.5"/>
    </pattern>
    <pattern id="major-grid" width="118.11023622047244" height="118.11023622047244" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="118.11023622047244" stroke="#707070" stroke-width="1"/>
      <line x1="0" y1="0" x2="118.11023622047244" y2="0" stroke="#707070" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="2126" height="2835" fill="url(#minor-grid)"/>
  <rect width="2126" height="2835" fill="url(#major-grid)"/>
  <line x1="531.496" y1="0" x2="531.496" y2="2835" stroke="#6699cc" stroke-width="1" stroke-dasharray="4,4" opacity="0.55"/>
  <line x1="1062.992" y1="0" x2="1062.992" y2="2835" stroke="#6699cc" stroke-width="1" stroke-dasharray="4,4" opacity="0.55"/>
  <line x1="1594.488" y1="0" x2="1594.488" y2="2835" stroke="#6699cc" stroke-width="1" stroke-dasharray="4,4" opacity="0.55"/>
  <line x1="2125.984" y1="0" x2="2125.984" y2="2835" stroke="#6699cc" stroke-width="1" stroke-dasharray="4,4" opacity="0.55"/>
</svg>`;

const GRID_LIGHT_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="2126" height="2835">
  <rect width="2126" height="2835" fill="#fdfcfa"/>
  <defs>
    <pattern id="minor-grid" width="11.811023622047244" height="11.811023622047244" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="11.811023622047244" stroke="#ccc8c4" stroke-width="0.5"/>
      <line x1="0" y1="0" x2="11.811023622047244" y2="0" stroke="#ccc8c4" stroke-width="0.5"/>
    </pattern>
    <pattern id="major-grid" width="118.11023622047244" height="118.11023622047244" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="118.11023622047244" stroke="#aaa6a2" stroke-width="1"/>
      <line x1="0" y1="0" x2="118.11023622047244" y2="0" stroke="#aaa6a2" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="2126" height="2835" fill="url(#minor-grid)"/>
  <rect width="2126" height="2835" fill="url(#major-grid)"/>
  <line x1="531.496" y1="0" x2="531.496" y2="2835" stroke="#4488aa" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
  <line x1="1062.992" y1="0" x2="1062.992" y2="2835" stroke="#4488aa" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
  <line x1="1594.488" y1="0" x2="1594.488" y2="2835" stroke="#4488aa" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
  <line x1="2125.984" y1="0" x2="2125.984" y2="2835" stroke="#4488aa" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
</svg>`;

function svgToDataUrl(svg: string): string {
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

export class GridManager {
  private gridEnabled: boolean = true;

  constructor(
    private canvas: any,
    private statusCallback?: (message: string) => void,
  ) {}

  /**
   * Draw grid using inline SVG data URI
   * @param isDark - Whether to use dark mode grid
   */
  public drawGrid(isDark: boolean = false): void {
    if (!this.canvas) return;

    const startTime = performance.now();

    // Clear old background image first to prevent stale grid showing during load
    this.canvas.setBackgroundImage(
      null,
      this.canvas.renderAll.bind(this.canvas),
    );

    // Use inline SVG data URI (bypasses HTTP serving issues)
    const gridDataUrl = svgToDataUrl(isDark ? GRID_DARK_SVG : GRID_LIGHT_SVG);

    const img = new Image();
    img.onload = () => {
      const fabricImg = new fabric.Image(img);
      this.canvas.setBackgroundImage(
        fabricImg,
        this.canvas.renderAll.bind(this.canvas),
        {
          scaleX: 1,
          scaleY: 1,
          originX: "left",
          originY: "top",
        },
      );

      const endTime = performance.now();
      console.log(
        `[GridManager] Grid loaded in ${(endTime - startTime).toFixed(2)}ms (${isDark ? "dark" : "light"} mode)`,
      );

      if (this.statusCallback) {
        this.statusCallback("Grid enabled");
      }
    };
    img.onerror = (err) => {
      console.error(`[GridManager] Failed to load grid SVG`, err);
    };
    img.src = gridDataUrl;
  }

  /**
   * Clear grid background from canvas
   */
  public clearGrid(): void {
    if (!this.canvas) return;

    // Determine current theme to restore proper background color
    const savedTheme =
      localStorage.getItem("canvas-theme") ||
      localStorage.getItem("scitex-theme-preference") ||
      "dark";
    const isDark = savedTheme === "dark";
    const bgColor = isDark ? "#2a2a2a" : "#fdfcfa";

    // Clear background image and restore solid background color
    this.canvas.setBackgroundImage(null, () => {
      this.canvas.backgroundColor = bgColor;
      this.canvas.renderAll();
    });

    console.log("[GridManager] Grid cleared");
  }

  /**
   * Toggle grid visibility
   */
  public toggleGrid(): void {
    this.gridEnabled = !this.gridEnabled;

    if (this.gridEnabled) {
      const savedTheme =
        localStorage.getItem("canvas-theme") ||
        localStorage.getItem("scitex-theme-preference") ||
        "dark";
      const isDark = savedTheme === "dark";
      this.drawGrid(isDark);
      console.log("[GridManager] Grid enabled");
    } else {
      this.clearGrid();
      if (this.statusCallback) {
        this.statusCallback("Grid disabled");
      }
      console.log("[GridManager] Grid disabled");
    }
  }

  public isGridEnabled(): boolean {
    return this.gridEnabled;
  }

  public enableGrid(): void {
    if (!this.gridEnabled) {
      this.toggleGrid();
    }
  }

  public disableGrid(): void {
    if (this.gridEnabled) {
      this.toggleGrid();
    }
  }
}
