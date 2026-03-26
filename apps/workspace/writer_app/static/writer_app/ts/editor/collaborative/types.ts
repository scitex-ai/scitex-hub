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

// --- WebSocket collaboration types ---

/** A remote collaborator as seen by the local client. */
export interface RemoteCollaborator {
  user_id: number;
  username: string;
  is_online: boolean;
  is_owner: boolean;
  current_section: string | null;
  cursor_position: CursorPosition | null;
  locked_sections: string[];
}

/** Cursor position within a section textarea. */
export interface CursorPosition {
  line: number;
  ch: number;
  /** Absolute character offset inside the textarea. */
  offset: number;
}

/** Inbound messages the server sends to the client. */
export type ServerMessage =
  | { type: "collaborators_list"; collaborators: ServerCollaborator[] }
  | {
      type: "user_joined";
      user_id: number;
      username: string;
      timestamp: string;
    }
  | { type: "user_left"; user_id: number; username: string; timestamp: string }
  | {
      type: "cursor_update";
      section: string;
      position: CursorPosition;
      user_id: number;
      username: string;
    }
  | {
      type: "section_locked";
      section: string;
      user_id: number;
      username: string;
      timestamp: string;
    }
  | {
      type: "section_unlocked";
      section: string;
      user_id: number;
      username: string;
      timestamp: string;
    }
  | {
      type: "text_change";
      section?: string;
      section_id?: string;
      operation: unknown;
      user_id: number;
      username?: string;
      timestamp: string;
    }
  | {
      type: "operation_submitted";
      operation_id: string;
      status: string;
      queue_length: number;
      current_version: number;
    }
  | { type: "operation_error"; operation_id: string; error: string }
  | { type: "lock_failed"; section: string; message: string }
  | { type: "error"; message: string }
  | { type: "undo_result"; success: boolean; [key: string]: unknown }
  | { type: "redo_result"; success: boolean; [key: string]: unknown }
  | { type: "undo_status"; section_id: string; [key: string]: unknown }
  | {
      type: "user_undone";
      user_id: number;
      username: string;
      section_id: string;
      timestamp: string;
    }
  | {
      type: "user_redone";
      user_id: number;
      username: string;
      section_id: string;
      timestamp: string;
    };

/** Shape of a collaborator entry from the server collaborators_list message. */
export interface ServerCollaborator {
  user_id: number;
  username: string;
  locked_sections: string[];
}

/** Callback map used by WriterWSClient subscribers. */
export interface WSEventCallbacks {
  onCollaboratorsList?: (collaborators: ServerCollaborator[]) => void;
  onUserJoined?: (userId: number, username: string) => void;
  onUserLeft?: (userId: number, username: string) => void;
  onCursorUpdate?: (
    userId: number,
    username: string,
    section: string,
    position: CursorPosition,
  ) => void;
  onSectionLocked?: (userId: number, username: string, section: string) => void;
  onSectionUnlocked?: (
    userId: number,
    username: string,
    section: string,
  ) => void;
  onTextChange?: (
    userId: number,
    section: string | undefined,
    sectionId: string | undefined,
    operation: unknown,
  ) => void;
  onOperationSubmitted?: (
    operationId: string,
    status: string,
    version: number,
  ) => void;
  onOperationError?: (operationId: string, error: string) => void;
  onLockFailed?: (section: string, message: string) => void;
  onConnectionChange?: (connected: boolean) => void;
}
