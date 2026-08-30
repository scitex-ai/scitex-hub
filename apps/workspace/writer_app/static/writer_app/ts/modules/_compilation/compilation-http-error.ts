/**
 * Turning a rejected compile request back into the reason it was rejected.
 *
 * Every compile call site used to do this:
 *
 *     if (!response.ok) throw new Error(`HTTP ${response.status}`);
 *
 * — and never read the body. The backend had already written the whole
 * explanation into that body; the UI threw it away and showed the user a
 * status code. Measured payloads that reached nobody (live scitex.ai,
 * 2026-08-17):
 *
 *   403 { error: "Read-only mode — sign up or log in to make changes.",
 *         reason: "readonly-visitor",
 *         detail: "Visitor slots are being prepared — you are browsing
 *                  read-only. Retry in a few minutes for a writable slot.",
 *         actions: ["signup","login","retry-later"],
 *         signup_url: "/auth/signup/", login_url: "/auth/login/" }
 *   404 { success:false, error: "Project 123 not found" }
 *   409 { success:false, error: "Preview compile is busy for this section,
 *                                please retry" }
 *
 * `HTTP 403` is not a reason. `HTTP 409` actively misleads — it looks like
 * a crash when the real answer is "retry in a moment".
 *
 * So: parse the body, carry `error` + `detail` in the thrown Error's own
 * message (the panels render `error.message`, and there are three of them),
 * and keep `reason` / `actions` / the auth urls as structured fields so a
 * caller can render Sign up / Log in instead of re-deriving them from
 * prose. Fall back to `HTTP <status>` ONLY when the body is not JSON —
 * a 502 from a proxy really does arrive as HTML, and inventing a reason
 * for it would be worse than the status code.
 */

/** The JSON shape Django's compile endpoints reject with. */
export interface CompilationErrorPayload {
  error?: string;
  detail?: string;
  reason?: string;
  actions?: string[];
  signup_url?: string;
  login_url?: string;
  success?: boolean;
  [key: string]: unknown;
}

export class CompilationHttpError extends Error {
  readonly status: number;
  readonly reason?: string;
  readonly detail?: string;
  readonly actions?: string[];
  readonly signupUrl?: string;
  readonly loginUrl?: string;
  readonly payload?: CompilationErrorPayload;

  constructor(
    message: string,
    status: number,
    payload?: CompilationErrorPayload,
  ) {
    super(message);
    this.name = "CompilationHttpError";
    this.status = status;
    this.payload = payload;
    this.reason = payload?.reason;
    this.detail = payload?.detail;
    this.actions = payload?.actions;
    this.signupUrl = payload?.signup_url;
    this.loginUrl = payload?.login_url;
  }

  /** True when the backend said this was the read-only visitor role. */
  get isReadonlyVisitor(): boolean {
    return this.reason === "readonly-visitor";
  }
}

/** The message a human should see, given a parsed rejection body. */
export function messageFromPayload(
  payload: CompilationErrorPayload | null,
  status: number,
): string {
  const parts = [payload?.error, payload?.detail]
    .filter((part): part is string => typeof part === "string")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);

  // `error` and `detail` are frequently the same sentence on simpler
  // endpoints; saying it twice reads like a bug.
  const unique = Array.from(new Set(parts));
  return unique.length > 0 ? unique.join(" ") : `HTTP ${status}`;
}

/**
 * Build the Error to throw for a non-OK compile response.
 *
 * Never throws itself: a malformed body must not replace the server's
 * rejection with a JSON parse error, which would be a second layer of
 * "the real reason was lost".
 */
export async function compilationErrorFromResponse(
  response: Response,
): Promise<CompilationHttpError> {
  let payload: CompilationErrorPayload | null = null;

  try {
    const text = await response.text();
    if (text) {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        payload = parsed as CompilationErrorPayload;
      }
    }
  } catch {
    // Not JSON (proxy HTML, empty body, truncated stream) — the status
    // code is genuinely all we know.
    payload = null;
  }

  return new CompilationHttpError(
    messageFromPayload(payload, response.status),
    response.status,
    payload ?? undefined,
  );
}

// EOF
