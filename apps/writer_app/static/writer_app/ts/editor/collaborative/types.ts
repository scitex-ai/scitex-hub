/**
 * Type Definitions for Collaborative Editor
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

export interface ManuscriptConfig {
  id: number;
  sections: string[];
}

export interface ManuscriptData {
  [sectionName: string]: string;
}

export interface VersionData {
  commit_message: string;
  version_tag: string;
  branch_name: string;
  is_major: boolean;
}

export interface VersionResponse {
  success: boolean;
  version?: {
    version_number: string;
  };
  error?: string;
}

export interface ExportData {
  manuscript_id: number;
  sections: ManuscriptData;
  exported_at: string;
}
