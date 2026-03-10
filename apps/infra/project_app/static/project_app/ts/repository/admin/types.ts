/**
 * Type definitions for repository maintenance
 * @module repository/admin/types
 */

export interface HealthStats {
  healthy_count: number;
  warnings: number;
  critical_issues: number;
  total_django_projects: number;
}

export interface RepositoryIssue {
  is_healthy: boolean;
  is_critical: boolean;
  project_slug?: string;
  gitea_name?: string;
  issue_type: string;
  message: string;
}

export interface HealthData {
  success: boolean;
  stats: HealthStats;
  issues: RepositoryIssue[];
  error?: string;
}

export interface PendingAction {
  type: "restore" | "delete" | "sync";
  name: string;
  projectName?: string;
}

export type FilterType = "all" | "healthy" | "warnings" | "critical";
