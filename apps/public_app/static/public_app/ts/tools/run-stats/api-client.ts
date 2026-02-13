/**
 * API Client for Statistics Calculator
 */

import type {
  StatsResult,
  PowerParams,
  RecommendationParams,
} from "./types.ts";

export class StatsApiClient {
  private baseUrl: string;

  constructor(baseUrl = "/api/stats") {
    this.baseUrl = baseUrl;
  }

  /**
   * Get descriptive statistics for a dataset
   */
  async describe(data: number[]): Promise<StatsResult> {
    return this.post("describe", { data });
  }

  /**
   * Run a statistical test
   */
  async calculate(
    testName: string,
    data?: number[],
    data2?: number[],
    groups?: number[][],
    alternative: string = "two-sided",
    plot: boolean = false,
  ): Promise<StatsResult> {
    const body: Record<string, any> = {
      test_name: testName,
      alternative,
      plot,
    };

    if (data !== undefined) body.data = data;
    if (data2 !== undefined) body.data2 = data2;
    if (groups !== undefined) body.groups = groups;

    return this.post("calculate", body);
  }

  /**
   * Calculate effect size
   */
  async effectSize(
    measure: string,
    group1?: number[],
    group2?: number[],
    params?: Record<string, any>,
  ): Promise<StatsResult> {
    const body: Record<string, any> = { measure };

    if (group1 !== undefined) body.group1 = group1;
    if (group2 !== undefined) body.group2 = group2;
    if (params !== undefined) {
      Object.assign(body, params);
    }

    return this.post("effect-size", body);
  }

  /**
   * Run post-hoc pairwise comparisons
   */
  async posthoc(
    method: string,
    groups: number[][],
    groupNames?: string[],
  ): Promise<StatsResult> {
    const body: Record<string, any> = {
      method,
      groups,
    };

    if (groupNames) body.group_names = groupNames;

    return this.post("posthoc", body);
  }

  /**
   * Calculate statistical power or sample size
   */
  async power(params: PowerParams): Promise<StatsResult> {
    return this.post("power", params);
  }

  /**
   * Apply multiple comparison correction
   */
  async correct(
    method: string,
    pvalues: number[],
    alpha: number = 0.05,
  ): Promise<StatsResult> {
    return this.post("correct", {
      method,
      pvalues,
      alpha,
    });
  }

  /**
   * Get test recommendations based on study design
   */
  async recommend(params: RecommendationParams): Promise<StatsResult> {
    return this.post("recommend", params);
  }

  /**
   * Generic POST request handler
   */
  private async post(
    endpoint: string,
    body: Record<string, any>,
  ): Promise<StatsResult> {
    try {
      const response = await fetch(`${this.baseUrl}/${endpoint}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCSRFToken(),
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const err = await response.json();
          errorMessage = err.error || errorMessage;
        } catch {
          // If JSON parsing fails, use the status text
          errorMessage = response.statusText || errorMessage;
        }
        return {
          success: false,
          result: {},
          error: errorMessage,
        };
      }

      return await response.json();
    } catch (error) {
      return {
        success: false,
        result: {},
        error: error instanceof Error ? error.message : "Network error",
      };
    }
  }

  /**
   * Get CSRF token from cookie
   */
  private getCSRFToken(): string {
    const name = "csrftoken";
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + "=")) {
        return trimmed.substring(name.length + 1);
      }
    }
    return "";
  }
}
