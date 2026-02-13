/**
 * Stats Calculator - Entry point
 */

import { StatsCalculator } from "./StatsCalculator.ts";

export { StatsCalculator } from "./StatsCalculator.ts";
export type {
  StatsTestConfig,
  StatsResult,
  WorkflowCategory,
} from "./types.ts";

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
