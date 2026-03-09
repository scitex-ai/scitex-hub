/**
 * Release Timeline Chart
 * Displays commit history and milestones using Chart.js
 */

declare const Chart: any;

interface CommitData {
  date: string;
  commits: number;
  cumulative: number;
  milestone: string | null;
}

interface ChartDataPoint {
  x: string;
  y: number;
  label?: string;
  commits?: number;
}

interface ThemeColors {
  lineColor: string;
  lineBgColor: string;
  milestoneColor: string;
  gridColor: string;
  textColor: string;
}

// Cumulative commit data by date
const commitData: CommitData[] = [
  { date: "2025-06-28", commits: 9, cumulative: 9, milestone: "Platform Launch" },
  { date: "2025-06-30", commits: 12, cumulative: 21, milestone: null },
  { date: "2025-07-01", commits: 6, cumulative: 27, milestone: "Project-Centric Architecture" },
  { date: "2025-10-16", commits: 45, cumulative: 73, milestone: "Design System" },
  { date: "2025-10-17", commits: 69, cumulative: 142, milestone: "Dark Mode & Templates" },
  { date: "2025-10-20", commits: 31, cumulative: 173, milestone: null },
  { date: "2025-10-22", commits: 57, cumulative: 230, milestone: null },
  { date: "2025-10-23", commits: 66, cumulative: 296, milestone: null },
  { date: "2025-10-24", commits: 39, cumulative: 335, milestone: null },
  { date: "2025-10-26", commits: 23, cumulative: 358, milestone: null },
  { date: "2025-10-27", commits: 39, cumulative: 397, milestone: "Code Blocks & Alerts" },
  { date: "2025-10-28", commits: 27, cumulative: 424, milestone: null },
  { date: "2025-10-29", commits: 7, cumulative: 431, milestone: "Writer API Layer" },
  { date: "2025-10-30", commits: 15, cumulative: 446, milestone: "Monaco Editor" },
  { date: "2025-11-01", commits: 10, cumulative: 456, milestone: null },
  { date: "2025-11-02", commits: 12, cumulative: 468, milestone: "SSL & Production" },
  { date: "2025-11-03", commits: 74, cumulative: 542, milestone: "Visitor Pool System" },
  { date: "2025-11-04", commits: 50, cumulative: 592, milestone: "TypeScript Migration" },
  { date: "2025-11-06", commits: 56, cumulative: 648, milestone: "Complete TS Migration" },
  { date: "2025-11-07", commits: 52, cumulative: 700, milestone: "Citation Autocomplete" },
  { date: "2025-11-08", commits: 13, cumulative: 713, milestone: null },
  { date: "2025-11-09", commits: 13, cumulative: 726, milestone: null },
  { date: "2025-11-11", commits: 43, cumulative: 769, milestone: "File Tree Modularization" },
  { date: "2025-11-12", commits: 30, cumulative: 799, milestone: null },
  { date: "2025-11-13", commits: 24, cumulative: 823, milestone: null },
  { date: "2025-11-14", commits: 21, cumulative: 844, milestone: null },
  { date: "2025-11-16", commits: 13, cumulative: 857, milestone: null },
  { date: "2025-11-17", commits: 14, cumulative: 871, milestone: null },
  { date: "2025-11-18", commits: 2, cumulative: 873, milestone: null },
  { date: "2025-11-19", commits: 1, cumulative: 874, milestone: null },
  { date: "2025-11-22", commits: 19, cumulative: 893, milestone: "Workspace Refactoring" },
  { date: "2025-11-23", commits: 19, cumulative: 912, milestone: null },
  { date: "2025-11-25", commits: 19, cumulative: 931, milestone: null },
  { date: "2025-11-26", commits: 14, cumulative: 945, milestone: "Symlink UI (v0.4.1-alpha)" },
  { date: "2025-11-27", commits: 15, cumulative: 960, milestone: "SLURM Terminal (v0.4.2-alpha)" },
  { date: "2025-11-28", commits: 12, cumulative: 972, milestone: "Database Renaming (v0.4.3-alpha)" },
  { date: "2025-11-29", commits: 8, cumulative: 980, milestone: null },
  { date: "2025-11-30", commits: 15, cumulative: 995, milestone: null },
  { date: "2025-12-01", commits: 6, cumulative: 1001, milestone: "File Tree Zoom (v0.4.4-alpha)" },
  { date: "2025-12-03", commits: 35, cumulative: 1036, milestone: "CrossRef Integration (v0.4.5-alpha)" },
  { date: "2025-12-06", commits: 89, cumulative: 1125, milestone: "Scholar Search UI (v0.4.6-alpha)" },
  { date: "2025-12-12", commits: 35, cumulative: 1160, milestone: "Vis Gallery (v0.5.0-alpha)" },
  { date: "2025-12-16", commits: 45, cumulative: 1205, milestone: "Element Inspector (v0.5.1-alpha)" },
];

/**
 * Get theme-aware colors for the chart
 */
function getThemeColors(): ThemeColors {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  return {
    lineColor: isDark ? "rgb(99, 179, 237)" : "rgb(59, 130, 246)",
    lineBgColor: isDark ? "rgba(99, 179, 237, 0.15)" : "rgba(59, 130, 246, 0.1)",
    milestoneColor: isDark ? "rgb(251, 146, 60)" : "rgb(249, 115, 22)",
    gridColor: isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)",
    textColor: isDark ? "rgb(226, 232, 240)" : "rgb(51, 65, 85)",
  };
}

/**
 * Initialize the commit timeline chart
 */
function initReleaseTimeline(): void {
  const ctx = document.getElementById("commitTimeline") as HTMLCanvasElement | null;
  if (!ctx) return;

  // Calculate true cumulative
  let cumulative = 0;
  const chartData = commitData.map((d) => {
    cumulative += d.commits;
    return { date: d.date, cumulative, milestone: d.milestone, commits: d.commits };
  });

  // Separate data for line and milestones
  const lineData: ChartDataPoint[] = chartData.map((d) => ({ x: d.date, y: d.cumulative }));
  const milestoneData: ChartDataPoint[] = chartData
    .filter((d) => d.milestone)
    .map((d) => ({ x: d.date, y: d.cumulative, label: d.milestone!, commits: d.commits }));

  let colors = getThemeColors();
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";

  const chart = new Chart(ctx, {
    type: "line",
    data: {
      datasets: [
        {
          label: "Cumulative Commits",
          data: lineData,
          borderColor: colors.lineColor,
          backgroundColor: colors.lineBgColor,
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: colors.lineColor,
          pointBorderColor: colors.lineColor,
        },
        {
          label: "Major Milestones",
          data: milestoneData,
          type: "scatter",
          backgroundColor: colors.milestoneColor,
          borderColor: isDark ? "rgba(0, 0, 0, 0.3)" : "rgba(255, 255, 255, 0.5)",
          borderWidth: 3,
          pointRadius: 8,
          pointHoverRadius: 12,
          pointStyle: "circle",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            usePointStyle: true,
            padding: 20,
            font: { size: 16, weight: "600" },
            color: colors.textColor,
            boxWidth: 20,
            boxHeight: 20,
          },
        },
        tooltip: {
          callbacks: {
            title: function (context: any) {
              if (context[0].dataset.label === "Major Milestones") {
                const point = milestoneData[context[0].dataIndex];
                return point.label;
              }
              return context[0].label;
            },
            label: function (context: any) {
              if (context.dataset.label === "Major Milestones") {
                const point = milestoneData[context.dataIndex];
                return `${point.commits} commits - Total: ${point.y}`;
              }
              return `Total Commits: ${context.parsed.y}`;
            },
          },
        },
      },
      scales: {
        x: {
          type: "time",
          time: { unit: "month", displayFormats: { month: "MMM yyyy" } },
          title: { display: true, text: "Development Timeline", color: colors.textColor },
          ticks: { color: colors.textColor },
          grid: { color: colors.gridColor },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: "Cumulative Commits", color: colors.textColor },
          ticks: { color: colors.textColor },
          grid: { color: colors.gridColor },
        },
      },
    },
  });

  // Listen for theme changes and update chart colors
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === "attributes" && mutation.attributeName === "data-theme") {
        colors = getThemeColors();
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";

        // Update dataset colors
        chart.data.datasets[0].borderColor = colors.lineColor;
        chart.data.datasets[0].backgroundColor = colors.lineBgColor;
        chart.data.datasets[0].pointBackgroundColor = colors.lineColor;
        chart.data.datasets[0].pointBorderColor = colors.lineColor;
        chart.data.datasets[1].backgroundColor = colors.milestoneColor;
        chart.data.datasets[1].borderColor = isDark ? "rgba(0, 0, 0, 0.3)" : "rgba(255, 255, 255, 0.5)";

        // Update scale colors
        chart.options.plugins.legend.labels.color = colors.textColor;
        chart.options.scales.x.title.color = colors.textColor;
        chart.options.scales.x.ticks.color = colors.textColor;
        chart.options.scales.x.grid.color = colors.gridColor;
        chart.options.scales.y.title.color = colors.textColor;
        chart.options.scales.y.ticks.color = colors.textColor;
        chart.options.scales.y.grid.color = colors.gridColor;

        chart.update();
      }
    });
  });

  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", initReleaseTimeline);
