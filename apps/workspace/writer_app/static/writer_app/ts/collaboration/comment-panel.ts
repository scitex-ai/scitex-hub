/**
 * Comment Panel for Manuscript Review
 *
 * Provides inline comment/annotation functionality for collaborative
 * paper review (David-sensei workflow).
 *
 * Features:
 * - List comments by section
 * - Create new comments with line range
 * - Reply to existing comment threads
 * - Resolve comment threads
 * - Real-time updates via WebSocket
 */

// ---------------------------------------------------------------
// Types
// ---------------------------------------------------------------

interface CommentAuthor {
  id: number;
  username: string;
}

interface CommentData {
  id: number;
  manuscript_id: number;
  author: CommentAuthor;
  section_id: string;
  line_start: number;
  line_end: number;
  text: string;
  parent_id: number | null;
  status: "open" | "resolved" | "closed";
  reply_count: number;
  created_at: string;
  updated_at: string;
}

type CommentFilter = "all" | "open" | "resolved";

// ---------------------------------------------------------------
// State
// ---------------------------------------------------------------

let comments: CommentData[] = [];
let currentFilter: CommentFilter = "open";
let currentSectionFilter: string = "";
let manuscriptId: number | null = null;
let panelElement: HTMLElement | null = null;

// ---------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------

function getCSRFToken(): string {
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="));
  return cookie ? cookie.split("=")[1] : "";
}

function apiBase(): string {
  return `/writer/collaboration/comments/${manuscriptId}`;
}

async function fetchComments(
  sectionId?: string,
  status?: string,
): Promise<CommentData[]> {
  const params = new URLSearchParams();
  if (sectionId) params.set("section_id", sectionId);
  if (status && status !== "all") params.set("status", status);
  params.set("parent_only", "true");

  const resp = await fetch(`${apiBase()}/?${params.toString()}`, {
    credentials: "same-origin",
  });
  const data = await resp.json();
  if (data.success) return data.comments;
  console.error("[CommentPanel] fetch error:", data.error);
  return [];
}

async function postComment(payload: {
  section_id: string;
  line_start: number;
  line_end: number;
  text: string;
  parent_id?: number | null;
}): Promise<CommentData | null> {
  const resp = await fetch(`${apiBase()}/create/`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  if (data.success) return data.comment;
  console.error("[CommentPanel] create error:", data.error);
  return null;
}

async function apiResolveComment(commentId: number): Promise<boolean> {
  const resp = await fetch(`${apiBase()}/${commentId}/resolve/`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCSRFToken() },
  });
  const data = await resp.json();
  return data.success === true;
}

async function apiDeleteComment(commentId: number): Promise<boolean> {
  const resp = await fetch(`${apiBase()}/${commentId}/delete/`, {
    method: "DELETE",
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCSRFToken() },
  });
  const data = await resp.json();
  return data.success === true;
}

// ---------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return d.toLocaleDateString();
}

function statusBadge(status: string): string {
  const colors: Record<string, string> = {
    open: "#ffa94d",
    resolved: "#51cf66",
    closed: "#868e96",
  };
  const color = colors[status] || "#868e96";
  return `<span style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;background:${color}22;color:${color};text-transform:capitalize;">${status}</span>`;
}

function renderCommentCard(c: CommentData): string {
  const replyInfo =
    c.reply_count > 0
      ? `<span style="font-size:11px;color:var(--workspace-text-secondary);margin-left:8px;">${c.reply_count} ${c.reply_count === 1 ? "reply" : "replies"}</span>`
      : "";

  const resolveBtn =
    c.status === "open"
      ? `<button class="comment-resolve-btn" data-comment-id="${c.id}" style="background:none;border:1px solid #51cf66;color:#51cf66;padding:2px 8px;border-radius:4px;font-size:11px;cursor:pointer;">Resolve</button>`
      : "";

  const deleteBtn = `<button class="comment-delete-btn" data-comment-id="${c.id}" style="background:none;border:1px solid #ff6b6b;color:#ff6b6b;padding:2px 8px;border-radius:4px;font-size:11px;cursor:pointer;margin-left:4px;">Delete</button>`;

  return `
    <div class="comment-card" data-comment-id="${c.id}" style="background:var(--workspace-bg-secondary);border:1px solid var(--workspace-border-default);border-radius:6px;padding:10px 12px;margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <div>
          <strong style="font-size:13px;color:var(--workspace-text-primary);">${c.author.username}</strong>
          <span style="font-size:11px;color:var(--workspace-text-tertiary);margin-left:6px;">${formatTimestamp(c.created_at)}</span>
          ${replyInfo}
        </div>
        ${statusBadge(c.status)}
      </div>
      <div style="font-size:12px;color:var(--workspace-text-secondary);margin-bottom:4px;">
        <code style="font-size:11px;background:var(--workspace-bg-tertiary,#2a2a2a);padding:1px 4px;border-radius:3px;">${c.section_id}</code>
        L${c.line_start}${c.line_end !== c.line_start ? "-L" + c.line_end : ""}
      </div>
      <div style="font-size:13px;color:var(--workspace-text-primary);line-height:1.5;white-space:pre-wrap;">${escapeHtml(c.text)}</div>
      <div style="display:flex;align-items:center;margin-top:8px;gap:4px;">
        ${resolveBtn}
        ${deleteBtn}
        <button class="comment-reply-btn" data-comment-id="${c.id}" data-section="${c.section_id}" data-line-start="${c.line_start}" data-line-end="${c.line_end}" style="background:none;border:1px solid var(--workspace-border-default);color:var(--workspace-text-secondary);padding:2px 8px;border-radius:4px;font-size:11px;cursor:pointer;margin-left:auto;">Reply</button>
      </div>
    </div>
  `;
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderPanel(): void {
  if (!panelElement) return;

  const filtered =
    currentFilter === "all"
      ? comments
      : comments.filter((c) => c.status === currentFilter);

  const sectionFiltered = currentSectionFilter
    ? filtered.filter((c) => c.section_id === currentSectionFilter)
    : filtered;

  const filterBtnStyle = (f: CommentFilter) => {
    const active = f === currentFilter;
    return `background:${active ? "var(--workspace-accent,#54aeff)" : "transparent"};color:${active ? "#fff" : "var(--workspace-text-secondary)"};border:1px solid ${active ? "var(--workspace-accent,#54aeff)" : "var(--workspace-border-default)"};padding:4px 10px;border-radius:4px;font-size:12px;cursor:pointer;`;
  };

  panelElement.innerHTML = `
    <div style="padding:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="margin:0;font-size:14px;font-weight:600;color:var(--workspace-text-primary);">Comments (${sectionFiltered.length})</h3>
        <div style="display:flex;gap:4px;">
          <button class="comment-filter-btn" data-filter="open" style="${filterBtnStyle("open")}">Open</button>
          <button class="comment-filter-btn" data-filter="resolved" style="${filterBtnStyle("resolved")}">Resolved</button>
          <button class="comment-filter-btn" data-filter="all" style="${filterBtnStyle("all")}">All</button>
        </div>
      </div>

      <div id="comment-new-form" style="margin-bottom:12px;padding:10px;background:var(--workspace-bg-secondary);border:1px solid var(--workspace-border-default);border-radius:6px;">
        <div style="display:flex;gap:6px;margin-bottom:6px;">
          <input id="comment-section-input" type="text" placeholder="Section (e.g. manuscript/methods)" style="flex:2;padding:4px 8px;font-size:12px;background:var(--workspace-bg-primary);color:var(--workspace-text-primary);border:1px solid var(--workspace-border-default);border-radius:4px;" />
          <input id="comment-line-start" type="number" placeholder="Line" min="1" style="width:60px;padding:4px 8px;font-size:12px;background:var(--workspace-bg-primary);color:var(--workspace-text-primary);border:1px solid var(--workspace-border-default);border-radius:4px;" />
          <span style="line-height:28px;color:var(--workspace-text-tertiary);">-</span>
          <input id="comment-line-end" type="number" placeholder="Line" min="1" style="width:60px;padding:4px 8px;font-size:12px;background:var(--workspace-bg-primary);color:var(--workspace-text-primary);border:1px solid var(--workspace-border-default);border-radius:4px;" />
        </div>
        <textarea id="comment-text-input" rows="2" placeholder="Add a comment..." style="width:100%;padding:6px 8px;font-size:12px;background:var(--workspace-bg-primary);color:var(--workspace-text-primary);border:1px solid var(--workspace-border-default);border-radius:4px;resize:vertical;box-sizing:border-box;"></textarea>
        <div style="display:flex;justify-content:flex-end;margin-top:6px;">
          <button id="comment-submit-btn" style="background:var(--workspace-accent,#54aeff);color:#fff;border:none;padding:4px 14px;border-radius:4px;font-size:12px;cursor:pointer;">Add Comment</button>
        </div>
      </div>

      <div id="comment-list">
        ${sectionFiltered.length === 0 ? '<div style="text-align:center;color:var(--workspace-text-tertiary);font-size:13px;padding:20px;">No comments yet.</div>' : sectionFiltered.map(renderCommentCard).join("")}
      </div>
    </div>
  `;

  bindPanelEvents();
}

// ---------------------------------------------------------------
// Event binding
// ---------------------------------------------------------------

function bindPanelEvents(): void {
  if (!panelElement) return;

  // Filter buttons
  panelElement
    .querySelectorAll<HTMLButtonElement>(".comment-filter-btn")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        currentFilter = (btn.dataset.filter || "open") as CommentFilter;
        renderPanel();
      });
    });

  // Submit new comment
  const submitBtn = panelElement.querySelector<HTMLButtonElement>(
    "#comment-submit-btn",
  );
  if (submitBtn) {
    submitBtn.addEventListener("click", handleSubmitComment);
  }

  // Resolve buttons
  panelElement
    .querySelectorAll<HTMLButtonElement>(".comment-resolve-btn")
    .forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.commentId);
        if (await apiResolveComment(id)) {
          await refreshComments();
        }
      });
    });

  // Delete buttons
  panelElement
    .querySelectorAll<HTMLButtonElement>(".comment-delete-btn")
    .forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.commentId);
        if (confirm("Delete this comment?")) {
          if (await apiDeleteComment(id)) {
            await refreshComments();
          }
        }
      });
    });

  // Reply buttons
  panelElement
    .querySelectorAll<HTMLButtonElement>(".comment-reply-btn")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const sectionInput = panelElement?.querySelector<HTMLInputElement>(
          "#comment-section-input",
        );
        const lineStartInput = panelElement?.querySelector<HTMLInputElement>(
          "#comment-line-start",
        );
        const lineEndInput =
          panelElement?.querySelector<HTMLInputElement>("#comment-line-end");
        const textInput = panelElement?.querySelector<HTMLTextAreaElement>(
          "#comment-text-input",
        );

        if (sectionInput) sectionInput.value = btn.dataset.section || "";
        if (lineStartInput) lineStartInput.value = btn.dataset.lineStart || "";
        if (lineEndInput) lineEndInput.value = btn.dataset.lineEnd || "";
        if (textInput) {
          textInput.focus();
          textInput.placeholder = `Reply to comment #${btn.dataset.commentId}...`;
          textInput.dataset.parentId = btn.dataset.commentId || "";
        }
      });
    });
}

async function handleSubmitComment(): Promise<void> {
  const sectionInput = panelElement?.querySelector<HTMLInputElement>(
    "#comment-section-input",
  );
  const lineStartInput = panelElement?.querySelector<HTMLInputElement>(
    "#comment-line-start",
  );
  const lineEndInput =
    panelElement?.querySelector<HTMLInputElement>("#comment-line-end");
  const textInput = panelElement?.querySelector<HTMLTextAreaElement>(
    "#comment-text-input",
  );

  if (!sectionInput || !lineStartInput || !lineEndInput || !textInput) return;

  const section = sectionInput.value.trim();
  const lineStart = parseInt(lineStartInput.value, 10);
  const lineEnd = parseInt(lineEndInput.value, 10) || lineStart;
  const text = textInput.value.trim();

  if (!section || !lineStart || !text) {
    alert("Please fill in section, line number, and comment text.");
    return;
  }

  const parentId = textInput.dataset.parentId
    ? Number(textInput.dataset.parentId)
    : null;

  const result = await postComment({
    section_id: section,
    line_start: lineStart,
    line_end: lineEnd,
    text: text,
    parent_id: parentId,
  });

  if (result) {
    // Clear form
    textInput.value = "";
    textInput.placeholder = "Add a comment...";
    delete textInput.dataset.parentId;
    await refreshComments();
  }
}

// ---------------------------------------------------------------
// Refresh / WebSocket integration
// ---------------------------------------------------------------

async function refreshComments(): Promise<void> {
  comments = await fetchComments(
    currentSectionFilter || undefined,
    currentFilter,
  );
  renderPanel();
}

/**
 * Handle incoming WebSocket comment events.
 * Call this from the main WebSocket message handler.
 */
export function handleCommentWebSocketEvent(data: {
  type: string;
  comment?: CommentData;
  comment_id?: number;
}): void {
  switch (data.type) {
    case "comment_created":
      if (data.comment) {
        comments.push(data.comment);
        renderPanel();
      }
      break;
    case "comment_resolved":
      if (data.comment_id) {
        const c = comments.find((x) => x.id === data.comment_id);
        if (c) c.status = "resolved";
        renderPanel();
      }
      break;
    case "comment_deleted":
      if (data.comment_id) {
        comments = comments.filter((x) => x.id !== data.comment_id);
        renderPanel();
      }
      break;
    case "comment_updated":
      if (data.comment) {
        const idx = comments.findIndex((x) => x.id === data.comment!.id);
        if (idx >= 0) comments[idx] = data.comment;
        renderPanel();
      }
      break;
  }
}

// ---------------------------------------------------------------
// Public API
// ---------------------------------------------------------------

/**
 * Initialize the comment panel.
 *
 * @param elementId - DOM element ID to mount the panel into
 * @param msId - Manuscript ID for API calls
 */
export async function initializeCommentPanel(
  elementId: string,
  msId: number,
): Promise<void> {
  console.log("[CommentPanel] Initializing...");

  manuscriptId = msId;
  panelElement = document.getElementById(elementId);

  if (!panelElement) {
    console.error(`[CommentPanel] Element #${elementId} not found`);
    return;
  }

  await refreshComments();
  console.log("[CommentPanel] Initialized with", comments.length, "comments");
}

/**
 * Set section filter from external code (e.g. when user switches sections).
 */
export function setCommentSectionFilter(sectionId: string): void {
  currentSectionFilter = sectionId;
  refreshComments();
}
