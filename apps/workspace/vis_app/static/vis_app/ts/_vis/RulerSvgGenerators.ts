/**
 * RulerSvgGenerators - SVG content generation for rulers
 *
 * Extracted from RulersManager.ts for file-size compliance.
 * Generates pre-rendered SVG strings for horizontal and vertical rulers
 * in both mm and inch units, with theme awareness.
 */

export interface RulerThemeColors {
  majorColor: string;
  textColor: string;
  minorColor: string;
  columnLabelColor: string;
}

/**
 * Get theme-aware colors for ruler rendering
 */
export function getRulerThemeColors(isDarkTheme: boolean): RulerThemeColors {
  return {
    majorColor: isDarkTheme ? "#ccc" : "#888",
    textColor: isDarkTheme ? "#aaa" : "#555",
    minorColor: isDarkTheme ? "#666" : "#aaa",
    columnLabelColor: isDarkTheme ? "#aaa" : "#555",
  };
}

/**
 * Generate horizontal ruler SVG with mm markings (pre-rendered)
 * PERFORMANCE: Returns complete SVG string instead of DOM manipulation
 * THEME-AWARE: Adapts colors based on isDarkTheme
 */
export function generateHorizontalRulerMm(
  width: number,
  dpi: number,
  rulerHeight: number,
  isDarkTheme: boolean,
): string {
  const pxToMm = (px: number) => (px / dpi) * 25.4;
  const mmToPx = (mm: number) => (mm * dpi) / 25.4;

  const { majorColor, textColor, minorColor, columnLabelColor } =
    getRulerThemeColors(isDarkTheme);

  const maxMm = pxToMm(width);
  const majorInterval = 10; // 10mm
  const middleInterval = 5; // 5mm
  const minorInterval = 1; // 1mm

  let svgContent = "";

  // Add 0mm tick mark at origin
  svgContent += `<line x1="0" y1="40" x2="0" y2="${rulerHeight}" stroke="${majorColor}" stroke-width="1.5"/>`;
  svgContent += `<text x="3" y="35" text-anchor="start" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer"><title>0mm (click to toggle inch)</title>0mm</text>`;

  // Generate all tick marks
  for (let mm = minorInterval; mm <= maxMm; mm += minorInterval) {
    const x = mmToPx(mm);

    if (mm % majorInterval === 0) {
      // Major tick (10mm)
      svgContent += `<line x1="${x}" y1="40" x2="${x}" y2="${rulerHeight}" stroke="${majorColor}" stroke-width="1.5"/>`;
      svgContent += `<text x="${x}" y="35" text-anchor="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer"><title>${mm}mm (click to toggle inch)</title>${mm}mm</text>`;
    } else if (mm % middleInterval === 0) {
      // Middle tick (5mm)
      svgContent += `<line x1="${x}" y1="48" x2="${x}" y2="${rulerHeight}" stroke="${majorColor}" stroke-width="1"/>`;
    } else {
      // Minor tick (1mm)
      svgContent += `<line x1="${x}" y1="54" x2="${x}" y2="${rulerHeight}" stroke="${minorColor}" stroke-width="0.5"/>`;
    }
  }

  // Add column width markers (0.5, 1.0, 1.5, 2.0 columns)
  const columnMarkers = [
    { mm: 45, label: "0.5 col" },
    { mm: 90, label: "1.0 col" },
    { mm: 135, label: "1.5 col" },
    { mm: 180, label: "2.0 col" },
  ];

  columnMarkers.forEach((marker) => {
    const x = mmToPx(marker.mm);
    if (x <= width) {
      svgContent += `<text x="${x}" y="12" text-anchor="middle" font-size="11" fill="${columnLabelColor}" font-weight="500">${marker.label}</text>`;
    }
  });

  return svgContent;
}

/**
 * Generate horizontal ruler SVG with inch markings (pre-rendered)
 * PERFORMANCE: Returns complete SVG string instead of DOM manipulation
 * THEME-AWARE: Adapts colors based on isDarkTheme
 */
export function generateHorizontalRulerInch(
  width: number,
  dpi: number,
  rulerHeight: number,
  isDarkTheme: boolean,
): string {
  const pxToInch = (px: number) => px / dpi;
  const inchToPx = (inch: number) => inch * dpi;

  const { majorColor, textColor, minorColor, columnLabelColor } =
    getRulerThemeColors(isDarkTheme);

  const maxInch = pxToInch(width);
  let svgContent = "";

  // Full inch markers
  for (let inch = 0; inch <= maxInch; inch++) {
    const x = inchToPx(inch);
    svgContent += `<line x1="${x}" y1="40" x2="${x}" y2="${rulerHeight}" stroke="${majorColor}" stroke-width="1.5"/>`;
    if (inch === 0) {
      // Special handling for 0" - position like mm ruler to avoid being cut off
      svgContent += `<text x="3" y="35" text-anchor="start" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer"><title>0" (click to toggle mm)</title>0"</text>`;
    } else {
      svgContent += `<text x="${x}" y="35" text-anchor="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer"><title>${inch}" (click to toggle mm)</title>${inch}"</text>`;
    }
  }

  // Fractional inch markers (1/2, 1/4, 1/8, 1/16)
  const fractions = [
    { divisor: 2, y: 48, stroke: majorColor, width: "1" },
    { divisor: 4, y: 51, stroke: majorColor, width: "0.8" },
    { divisor: 8, y: 54, stroke: minorColor, width: "0.6" },
    { divisor: 16, y: 56, stroke: minorColor, width: "0.4" },
  ];

  fractions.forEach((frac) => {
    for (let inch = 0; inch <= maxInch; inch++) {
      for (let i = 1; i < frac.divisor; i++) {
        if (i % 2 === 0 && frac.divisor > 2) continue;
        if (i % 4 === 0 && frac.divisor > 4) continue;
        if (i % 8 === 0 && frac.divisor > 8) continue;

        const position = inch + i / frac.divisor;
        const x = inchToPx(position);

        if (x <= width) {
          svgContent += `<line x1="${x}" y1="${frac.y}" x2="${x}" y2="${rulerHeight}" stroke="${frac.stroke}" stroke-width="${frac.width}"/>`;
        }
      }
    }
  });

  // Column width markers (convert from mm to inch)
  const columnMarkersInch = [
    { inch: 45 / 25.4, label: "0.5 col" },
    { inch: 90 / 25.4, label: "1.0 col" },
    { inch: 135 / 25.4, label: "1.5 col" },
    { inch: 180 / 25.4, label: "2.0 col" },
  ];

  columnMarkersInch.forEach((marker) => {
    const x = inchToPx(marker.inch);
    if (x <= width) {
      svgContent += `<text x="${x}" y="12" text-anchor="middle" font-size="11" fill="${columnLabelColor}" font-weight="500">${marker.label}</text>`;
    }
  });

  return svgContent;
}

/**
 * Generate vertical ruler SVG with mm markings (pre-rendered)
 * PERFORMANCE: Returns complete SVG string instead of DOM manipulation
 * THEME-AWARE: Adapts colors based on isDarkTheme
 */
export function generateVerticalRulerMm(
  height: number,
  dpi: number,
  rulerWidth: number,
  isDarkTheme: boolean,
): string {
  const pxToMm = (px: number) => (px / dpi) * 25.4;
  const mmToPx = (mm: number) => (mm * dpi) / 25.4;

  const { majorColor, textColor, minorColor } =
    getRulerThemeColors(isDarkTheme);

  const maxMm = pxToMm(height);
  const majorInterval = 10; // 10mm
  const middleInterval = 5; // 5mm
  const minorInterval = 1; // 1mm

  let svgContent = "";

  // Add 0mm tick mark at origin
  svgContent += `<line x1="40" y1="0" x2="${rulerWidth}" y2="0" stroke="${majorColor}" stroke-width="1.5"/>`;
  svgContent += `<text x="30" y="8" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer" transform="rotate(-90, 30, 8)"><title>0mm (click to toggle inch)</title>0mm</text>`;

  for (let mm = minorInterval; mm <= maxMm; mm += minorInterval) {
    const y = mmToPx(mm);

    if (mm % majorInterval === 0) {
      // Major tick
      svgContent += `<line x1="40" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${majorColor}" stroke-width="1.5"/>`;
      svgContent += `<text x="30" y="${y}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer" transform="rotate(-90, 30, ${y})"><title>${mm}mm (click to toggle inch)</title>${mm}mm</text>`;
    } else if (mm % middleInterval === 0) {
      // Middle tick
      svgContent += `<line x1="48" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${majorColor}" stroke-width="1"/>`;
    } else {
      // Minor tick
      svgContent += `<line x1="54" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${minorColor}" stroke-width="0.5"/>`;
    }
  }

  return svgContent;
}

/**
 * Generate vertical ruler SVG with inch markings (pre-rendered)
 * PERFORMANCE: Returns complete SVG string instead of DOM manipulation
 * THEME-AWARE: Adapts colors based on isDarkTheme
 */
export function generateVerticalRulerInch(
  height: number,
  dpi: number,
  rulerWidth: number,
  isDarkTheme: boolean,
): string {
  const pxToInch = (px: number) => px / dpi;
  const inchToPx = (inch: number) => inch * dpi;

  const { majorColor, textColor, minorColor } =
    getRulerThemeColors(isDarkTheme);

  const maxInch = pxToInch(height);
  let svgContent = "";

  // Full inch markers
  for (let inch = 0; inch <= maxInch; inch++) {
    const y = inchToPx(inch);
    svgContent += `<line x1="40" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${majorColor}" stroke-width="1.5"/>`;
    if (inch === 0) {
      // Special handling for 0" - position like mm ruler to avoid being cut off
      svgContent += `<text x="30" y="8" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer" transform="rotate(-90, 30, 8)"><title>0" (click to toggle mm)</title>0"</text>`;
    } else {
      svgContent += `<text x="30" y="${y}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${textColor}" class="ruler-label" style="cursor:pointer" transform="rotate(-90, 30, ${y})"><title>${inch}" (click to toggle mm)</title>${inch}"</text>`;
    }
  }

  // Fractional inch markers
  const fractions = [
    { divisor: 2, x: 48, stroke: majorColor, width: "1" },
    { divisor: 4, x: 51, stroke: majorColor, width: "0.8" },
    { divisor: 8, x: 54, stroke: minorColor, width: "0.6" },
    { divisor: 16, x: 56, stroke: minorColor, width: "0.4" },
  ];

  fractions.forEach((frac) => {
    for (let inch = 0; inch <= maxInch; inch++) {
      for (let i = 1; i < frac.divisor; i++) {
        if (i % 2 === 0 && frac.divisor > 2) continue;
        if (i % 4 === 0 && frac.divisor > 4) continue;
        if (i % 8 === 0 && frac.divisor > 8) continue;

        const position = inch + i / frac.divisor;
        const y = inchToPx(position);

        if (y <= height) {
          svgContent += `<line x1="${frac.x}" y1="${y}" x2="${rulerWidth}" y2="${y}" stroke="${frac.stroke}" stroke-width="${frac.width}"/>`;
        }
      }
    }
  });

  return svgContent;
}
