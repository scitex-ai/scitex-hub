/**
 * Collaboration session page functionality
 * Corresponds to: templates/writer_app/collaboration/session.html
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/collaboration/session.ts loaded",
);
interface CollaboratorPresence {
  user_id: number;
  username: string;
  is_active: boolean;
}

class CollaborationSessionPage {
  private _websocket: WebSocket | null = null;
  private _collaborators: Map<number, CollaboratorPresence>;

  constructor() {
    this._collaborators = new Map();
    this.init();
  }

  private init(): void {
    console.log("[CollaborationSession] Initializing collaboration session");
    this.setupWebSocket();
  }

  private setupWebSocket(): void {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/writer/collaboration/`;
    console.log("[CollaborationSession] Connecting to WebSocket:", wsUrl);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new CollaborationSessionPage();
});
