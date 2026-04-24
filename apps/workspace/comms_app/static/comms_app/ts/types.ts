/**
 * TypeScript interfaces for the Comms app.
 *
 * Mirrors the DRF serializers and WebSocket payloads
 * from the backend consumer (CommsConsumer).
 */

/** Participant identity -- human user or AI agent. */
export interface Participant {
  id: number;
  participant_type: "user" | "agent";
  display_name: string;
  agent_name?: string;
  avatar_url: string;
  is_online: boolean;
  last_seen: string | null;
  created_at: string;
}

/** Channel metadata. */
export interface Channel {
  id: number;
  name: string;
  slug: string;
  description: string;
  channel_type: "public" | "private" | "direct" | "agent";
  project: number | null;
  created_by: Participant | null;
  is_archived: boolean;
  member_count: number;
  created_at: string;
  updated_at: string;
}

/** A single message. */
export interface Message {
  id: number;
  channel_id: number;
  sender: MessageSender | null;
  text: string;
  attachments: Record<string, unknown>[];
  parent_id: number | null;
  is_edited: boolean;
  edited_at: string | null;
  is_deleted?: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  /** Client-side computed field: number of thread replies (populated by UI). */
  reply_count?: number;
}

/** Sender info embedded in a Message payload. */
export interface MessageSender {
  id: number;
  display_name: string;
  participant_type: "user" | "agent";
}

// --------------------------------------------------------------------- events

/** Server -> Client event types from CommsConsumer. */
export type ServerEventType =
  | "message.new"
  | "message.edited"
  | "typing.indicator"
  | "presence.update"
  | "error";

/** Payload for message.new / message.edited events. */
export interface MessageEvent {
  type: "message.new" | "message.edited";
  message: Message;
}

/** Payload for typing.indicator event. */
export interface TypingEvent {
  type: "typing.indicator";
  participant: MessageSender;
  is_typing: boolean;
}

/** Payload for presence.update event. */
export interface PresenceEvent {
  type: "presence.update";
  participant: MessageSender;
  is_online: boolean;
}

/** Payload for error event. */
export interface ErrorEvent {
  type: "error";
  detail: string;
}

/** Union of all server events. */
export type ServerEvent =
  | MessageEvent
  | TypingEvent
  | PresenceEvent
  | ErrorEvent;

/** Handler callback for a specific event type. */
export type EventHandler<T = ServerEvent> = (data: T) => void;
