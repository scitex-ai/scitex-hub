/**
 * Stats Calculator - Entry point
 */

import { StatsCalculator } from "./_StatsCalculator";

export { StatsCalculator } from "./_StatsCalculator";
export type { StatsTestConfig, StatsResult, WorkflowCategory } from "./types";

let instance: StatsCalculator | null = null;

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("stats-data-table");
  if (container) {
    instance = new StatsCalculator();
    console.log("[StatsCalculator] Initialized");
  }
});

export function getInstance(): StatsCalculator | null {
  return instance;
}
