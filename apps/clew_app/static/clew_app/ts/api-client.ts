/**
 * Clew API Client
 * Thin wrapper around the Django API endpoints
 */

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface VerificationStatus {
  verified_count: number;
  mismatch_count: number;
  missing_count: number;
  mismatched: Array<{
    session_id: string;
    files: string[];
  }>;
  missing: Array<{
    session_id: string;
    files: string[];
  }>;
}

export interface RunInfo {
  session_id: string;
  script_path: string;
  script_hash: string;
  started_at: string;
  finished_at: string;
  status: string;
  exit_code: number;
  parent_session: string | null;
  combined_hash: string;
  metadata: string | null;
}

export interface FileVerification {
  path: string;
  role: string;
  expected_hash: string;
  current_hash: string | null;
  status: "verified" | "mismatch" | "missing" | "unknown";
  is_verified: boolean;
}

export interface RunVerification {
  session_id: string;
  script_path: string | null;
  status: "verified" | "mismatch" | "missing" | "unknown";
  is_verified: boolean;
  is_verified_from_scratch: boolean;
  combined_hash_expected: string | null;
  combined_hash_current: string | null;
  files: FileVerification[];
}

export interface ChainVerification {
  target_file: string;
  status: "verified" | "mismatch" | "missing" | "unknown";
  is_verified: boolean;
  runs: RunVerification[];
}

export interface DagNode {
  id: string;
  type: "script" | "file";
  name: string;
  path: string;
  status: "verified" | "failed";
  hash: string | null;
  session_id?: string;
  role?: "input" | "output";
  verified_from_scratch?: boolean;
}

export interface DagLink {
  source: string;
  target: string;
  type: "input" | "output";
}

export interface DagData {
  nodes: DagNode[];
  links: DagLink[];
  metadata: {
    generated_at: string;
    target_file?: string;
    session_id?: string;
    num_runs: number;
    num_files: number;
    empty?: boolean;
  };
}

export interface DatabaseStats {
  total_runs: number;
  success_runs: number;
  failed_runs: number;
  total_file_records: number;
  unique_files: number;
  db_path: string;
}

export interface ClaimInfo {
  claim_id: string;
  file_path: string;
  line_number: number | null;
  claim_type: "statistic" | "figure" | "table" | "text" | "value";
  claim_value: string | null;
  source_session: string | null;
  source_file: string | null;
  source_hash: string | null;
  registered_at: string | null;
  verified_at: string | null;
  status: "registered" | "verified" | "mismatch" | "missing" | "partial";
}

export class ClewApiClient {
  private baseUrl = "/apps/clew/api";

  private getCsrf(): string {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
  }

  private async fetchJson<T>(
    endpoint: string,
    params?: Record<string, string>,
    method: "GET" | "POST" = "GET",
  ): Promise<ApiResponse<T>> {
    const url = new URL(`${this.baseUrl}${endpoint}`, window.location.origin);
    if (method === "GET" && params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }

    try {
      const init: RequestInit =
        method === "POST"
          ? {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": this.getCsrf(),
              },
              body: JSON.stringify(params ?? {}),
            }
          : {};
      const response = await fetch(url.toString(), init);
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : "Unknown error occurred",
      };
    }
  }

  /**
   * Get verification status summary (like git status)
   */
  async getStatus(): Promise<ApiResponse<VerificationStatus>> {
    return this.fetchJson<VerificationStatus>("/status/");
  }

  /**
   * Get database statistics
   */
  async getStats(): Promise<ApiResponse<DatabaseStats>> {
    return this.fetchJson<DatabaseStats>("/stats/");
  }

  /**
   * List tracked runs with optional filtering
   */
  async listRuns(params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<
    ApiResponse<{
      runs: RunInfo[];
      count: number;
      limit: number;
      offset: number;
    }>
  > {
    const queryParams: Record<string, string> = {};
    if (params?.limit !== undefined)
      queryParams.limit = params.limit.toString();
    if (params?.offset !== undefined)
      queryParams.offset = params.offset.toString();
    if (params?.status) queryParams.status = params.status;

    return this.fetchJson("/runs/", queryParams);
  }

  /**
   * Verify a specific run by session ID
   */
  async verifyRun(
    sessionId: string,
    fromScratch = false,
  ): Promise<ApiResponse<RunVerification>> {
    return this.fetchJson<RunVerification>("/verify-run/", {
      session_id: sessionId,
      from_scratch: fromScratch.toString(),
    });
  }

  /**
   * Verify the dependency chain for a target file
   */
  async verifyChain(
    targetPath: string,
  ): Promise<ApiResponse<ChainVerification>> {
    return this.fetchJson<ChainVerification>("/verify-chain/", {
      target: targetPath,
    });
  }

  /**
   * Get DAG data as JSON for visualization
   */
  async getDagJson(params?: {
    sessionId?: string;
    targetFile?: string;
    pathMode?: "name" | "relative" | "absolute";
  }): Promise<ApiResponse<DagData>> {
    const queryParams: Record<string, string> = {};
    if (params?.sessionId) queryParams.session_id = params.sessionId;
    if (params?.targetFile) queryParams.target_file = params.targetFile;
    if (params?.pathMode) queryParams.path_mode = params.pathMode;

    return this.fetchJson<DagData>("/dag/json/", queryParams);
  }

  /**
   * Get Mermaid diagram code for DAG visualization
   */
  async getMermaidDag(params?: {
    sessionId?: string;
    targetFile?: string;
    targetFiles?: string[];
    claims?: boolean;
    showHashes?: boolean;
    pathMode?: "name" | "relative" | "absolute";
  }): Promise<ApiResponse<{ mermaid: string }>> {
    const queryParams: Record<string, string> = {};
    if (params?.sessionId) queryParams.session_id = params.sessionId;
    if (params?.targetFile) queryParams.target_file = params.targetFile;
    if (params?.targetFiles?.length)
      queryParams.target_files = params.targetFiles.join(",");
    if (params?.claims) queryParams.claims = "true";
    if (params?.showHashes !== undefined)
      queryParams.show_hashes = params.showHashes.toString();
    if (params?.pathMode) queryParams.path_mode = params.pathMode;

    return this.fetchJson<{ mermaid: string }>("/dag/mermaid/", queryParams);
  }

  /**
   * List registered claims with optional filtering
   */
  async listClaims(params?: {
    filePath?: string;
    claimType?: string;
    status?: string;
    limit?: number;
  }): Promise<
    ApiResponse<{
      claims: import("./api-client").ClaimInfo[];
      count: number;
    }>
  > {
    const queryParams: Record<string, string> = {};
    if (params?.filePath) queryParams.file_path = params.filePath;
    if (params?.claimType) queryParams.claim_type = params.claimType;
    if (params?.status) queryParams.status = params.status;
    if (params?.limit !== undefined)
      queryParams.limit = params.limit.toString();

    return this.fetchJson("/claims/", queryParams);
  }

  /**
   * Add example Clew pipeline scripts to the current project
   */
  async addExamples(): Promise<ApiResponse<{ message: string }>> {
    return this.fetchJson<{ message: string }>("/add-examples/", {}, "POST");
  }
}

// Export singleton instance
export const clewApi = new ClewApiClient();
