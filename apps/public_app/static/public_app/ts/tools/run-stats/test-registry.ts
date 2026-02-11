/**
 * Test Registry - Central definition of all statistical tests
 */

import type {
  StatsTestConfig,
  CategoryInfo,
  WorkflowCategory,
} from "./types.ts";

export const WORKFLOW_CATEGORIES: Record<WorkflowCategory, CategoryInfo> = {
  describe: {
    label: "1. Describe",
    description: "Summarize data with descriptive statistics",
  },
  assume: {
    label: "2. Assumptions",
    description: "Test assumptions (normality, homogeneity)",
  },
  compare: {
    label: "3. Compare",
    description: "Statistical tests to compare groups or variables",
  },
  posthoc: {
    label: "4. Post-hoc",
    description: "Pairwise comparisons after significant omnibus test",
  },
  effect: {
    label: "5. Effect Size",
    description: "Measure magnitude of differences or relationships",
  },
  power: {
    label: "6. Power",
    description: "Calculate statistical power or required sample size",
  },
  correct: {
    label: "7. Correction",
    description: "Multiple comparison correction for p-values",
  },
};

export const TEST_REGISTRY: Record<string, StatsTestConfig> = {
  // ===== 1. DESCRIBE =====
  descriptive: {
    id: "descriptive",
    name: "Descriptive Stats",
    category: "describe",
    dataMode: "single",
    description: "Mean, median, SD, quartiles, min/max",
    endpoint: "describe",
  },

  // ===== 2. ASSUMPTIONS =====
  shapiro: {
    id: "shapiro",
    name: "Shapiro-Wilk",
    category: "assume",
    dataMode: "single",
    description: "Test normality of distribution",
    endpoint: "calculate",
    testName: "shapiro",
  },

  // ===== 3. COMPARE =====
  ttest_ind: {
    id: "ttest_ind",
    name: "t-test (Independent)",
    category: "compare",
    dataMode: "paired",
    description: "Compare means of two independent groups",
    endpoint: "calculate",
    testName: "ttest_ind",
  },
  ttest_paired: {
    id: "ttest_paired",
    name: "t-test (Paired)",
    category: "compare",
    dataMode: "paired",
    description: "Compare means of two related samples",
    endpoint: "calculate",
    testName: "ttest_rel",
  },
  anova: {
    id: "anova",
    name: "ANOVA",
    category: "compare",
    dataMode: "groups",
    description: "Compare means of 3+ independent groups",
    endpoint: "calculate",
    testName: "anova",
  },
  pearson: {
    id: "pearson",
    name: "Pearson Correlation",
    category: "compare",
    dataMode: "paired",
    description: "Linear correlation between two continuous variables",
    endpoint: "calculate",
    testName: "pearson",
  },
  mannwhitney: {
    id: "mannwhitney",
    name: "Mann-Whitney U",
    category: "compare",
    dataMode: "paired",
    description: "Non-parametric comparison of two independent groups",
    endpoint: "calculate",
    testName: "mannwhitneyu",
  },
  wilcoxon: {
    id: "wilcoxon",
    name: "Wilcoxon Signed-Rank",
    category: "compare",
    dataMode: "paired",
    description: "Non-parametric comparison of two related samples",
    endpoint: "calculate",
    testName: "wilcoxon",
  },
  kruskal: {
    id: "kruskal",
    name: "Kruskal-Wallis",
    category: "compare",
    dataMode: "groups",
    description: "Non-parametric comparison of 3+ groups",
    endpoint: "calculate",
    testName: "kruskal",
  },
  spearman: {
    id: "spearman",
    name: "Spearman Correlation",
    category: "compare",
    dataMode: "paired",
    description: "Non-parametric rank correlation",
    endpoint: "calculate",
    testName: "spearman",
  },
  brunnermunzel: {
    id: "brunnermunzel",
    name: "Brunner-Munzel",
    category: "compare",
    dataMode: "paired",
    description:
      "Robust nonparametric test for two independent groups (no equal shape assumption)",
    endpoint: "calculate",
    testName: "brunnermunzel",
  },
  chi2: {
    id: "chi2",
    name: "Chi-Square",
    category: "compare",
    dataMode: "groups",
    description: "Test independence in contingency table",
    endpoint: "calculate",
    testName: "chi2",
  },

  // ===== 4. POST-HOC =====
  tukey: {
    id: "tukey",
    name: "Tukey HSD",
    category: "posthoc",
    dataMode: "groups",
    description: "Pairwise comparisons after ANOVA (equal variance)",
    endpoint: "posthoc",
    method: "tukey",
  },
  games_howell: {
    id: "games_howell",
    name: "Games-Howell",
    category: "posthoc",
    dataMode: "groups",
    description: "Pairwise comparisons (unequal variance)",
    endpoint: "posthoc",
    method: "games-howell",
  },
  dunnett: {
    id: "dunnett",
    name: "Dunnett",
    category: "posthoc",
    dataMode: "groups",
    description: "Compare all groups to control group",
    endpoint: "posthoc",
    method: "dunnett",
  },

  // ===== 5. EFFECT SIZE =====
  cohens_d: {
    id: "cohens_d",
    name: "Cohen's d",
    category: "effect",
    dataMode: "paired",
    description: "Standardized mean difference",
    endpoint: "effect-size",
    measure: "cohens_d",
  },
  eta_squared: {
    id: "eta_squared",
    name: "Eta-squared",
    category: "effect",
    dataMode: "params",
    description: "Proportion of variance explained (ANOVA)",
    endpoint: "effect-size",
    measure: "eta_squared",
  },
  epsilon_squared: {
    id: "epsilon_squared",
    name: "Epsilon-squared",
    category: "effect",
    dataMode: "params",
    description: "Less biased effect size for ANOVA",
    endpoint: "effect-size",
    measure: "epsilon_squared",
  },
  cliffs_delta: {
    id: "cliffs_delta",
    name: "Cliff's Delta",
    category: "effect",
    dataMode: "paired",
    description: "Non-parametric effect size (-1 to +1)",
    endpoint: "effect-size",
    measure: "cliffs_delta",
  },
  prob_superiority: {
    id: "prob_superiority",
    name: "Probability of Superiority",
    category: "effect",
    dataMode: "paired",
    description: "Probability random value from A > B",
    endpoint: "effect-size",
    measure: "prob_superiority",
  },

  // ===== 6. POWER =====
  power_ttest: {
    id: "power_ttest",
    name: "T-Test Power",
    category: "power",
    dataMode: "params",
    description: "Calculate power for t-test given parameters",
    endpoint: "power",
    testType: "ttest",
  },
  sample_size: {
    id: "sample_size",
    name: "Sample Size",
    category: "power",
    dataMode: "params",
    description: "Calculate required n for desired power",
    endpoint: "power",
    testType: "ttest",
  },

  // ===== 7. CORRECTION =====
  bonferroni: {
    id: "bonferroni",
    name: "Bonferroni",
    category: "correct",
    dataMode: "pvalues",
    description: "Conservative correction (α/m)",
    endpoint: "correct",
    method: "bonferroni",
  },
  fdr_bh: {
    id: "fdr_bh",
    name: "FDR (Benjamini-Hochberg)",
    category: "correct",
    dataMode: "pvalues",
    description: "False discovery rate control",
    endpoint: "correct",
    method: "fdr_bh",
  },
  holm: {
    id: "holm",
    name: "Holm-Bonferroni",
    category: "correct",
    dataMode: "pvalues",
    description: "Sequentially rejective Bonferroni",
    endpoint: "correct",
    method: "holm",
  },
  sidak: {
    id: "sidak",
    name: "Sidak",
    category: "correct",
    dataMode: "pvalues",
    description: "Less conservative than Bonferroni",
    endpoint: "correct",
    method: "sidak",
  },
};
