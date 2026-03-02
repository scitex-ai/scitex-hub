/**
 * Tables Panel Types
 * Shared type definitions for tables panel modules
 */

export interface Table {
  id?: number;
  label?: string; // For backwards compatibility
  file_name: string;
  file_path: string;
  file_type?: string;
  file_size?: number;
  file_hash?: string;
  caption?: string;
  dimensions?: string;
  thumbnail_url?: string;
  thumbnail_path?: string;
  width?: number;
  height?: number;
  tags?: string[];
  is_referenced?: number | boolean;
  reference_count?: number;
  source?: string;
  location?: string;
  last_modified?: number;
}
