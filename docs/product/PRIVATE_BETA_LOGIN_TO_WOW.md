# SciTeX™ Cloud Private Beta: Login-to-Wow Journey

Status: product SSOT for the Private Beta release  
Owner: scitex-hub product lead  
Source: operator-led desktop walkthrough on 2026-09-17  
Scope: desktop first; 390 px mobile follows after the desktop journey is coherent

## North star

A first-time researcher reaches `scitex.ai`, understands the value, creates an
account, creates their own project, and completes a real research workflow
without re-uploading or re-selecting context:

1. Arrive and understand the outcome SciTeX provides.
2. Create an account, verify email, and complete the trial/payment step.
3. Receive a stable Linux identity and private persistent 32 GB workspace.
4. Create or import a project explicitly; never silently select an example.
5. Find and save literature in Scholar.
6. Analyze project data in Stats.
7. create a publication figure in FigRecipe.
8. Compile a manuscript PDF in Writer.
9. Ask Chat for help at any point, including before adding a personal provider.
10. Return later and resume the same project, files, apps, and outputs.

The wow moment is not an isolated app screen. It is the realization that one
project connects literature, data, figures, manuscript, compute, collaborators,
and agents.

## Non-negotiable product rules

- Project context is selected once and carried across every leaf app.
- Hub owns identity, routing, project/user context, integration, billing,
  deployment, and the end-to-end journey. Leaf packages own domain logic.
- `scitex-ui` owns shared semantic tokens, shell primitives, responsive behavior,
  project selector, first-use tour primitives, and dock behavior.
- Real users never receive a silently created or selected example project.
- There is no visitor, guest, or shared execution identity.
- Signed-in users receive one stable Linux identity, an NAS-02-backed 32 GB
  workspace, and scheduler-accounted compute access.
- UI actions map to stable named commands so mouse, touch, keyboard, macros, and
  agents invoke the same operations.
- The public product uses SciTeX semantic brand tokens: navy primary and muted
  gold accent. Leaf apps may extend but should inherit SDK defaults.
- Every production entry point has loading, empty, denied, unavailable, retry,
  and success states; no customer-facing "preparing" placeholder.
- Desktop is completed and measured before adapting the same contracts to 390 px.

## 1. Public landing page

### Problem

The current first viewport leads with a technical "built in 40 minutes" proof.
Then it presents product names (Scholar, Writer, FigRecipe, On-Premise) before a
new customer knows what they do. Pricing mixes hosted plans, self-hosting,
future features, and unclear trial terms.

### Required experience

- Lead with the customer outcome: one connected workspace from literature to a
  publication-ready paper.
- Present workflow tasks before internal product names:
  - Find and organize literature — Scholar.
  - Analyze research data — Stats.
  - Create publication figures — FigRecipe.
  - Write and compile the manuscript — Writer.
- Keep the timed demo as secondary evidence. Label measured workflow time and
  playback duration separately; move MCP details into a technical section.
- Move Self-Hosted out of the app-card row into a deployment section.
- Pricing clearly separates Academic Cloud, Professional Cloud, Self-Hosted
  Community, and Self-Hosted Commercial.
- Included features must be available now; "Coming soon" is not an entitlement.
- State billing interval, currency, trial duration, card requirement, conversion
  date, cancellation behavior, taxes, storage, and compute/usage limits.

## 2. Signup, verification, and trial activation

### Funnel

1. Account details.
2. Six-digit email verification.
3. Stripe Checkout or Payment Element.
4. Trial becomes active and the user enters onboarding.

Google and ORCID sign-in rejoin the same verified-email/payment state machine.
Raw card number and CVC never reach SciTeX servers.

### Form behavior

- Remove password confirmation; email verification and password reset provide
  the recovery path.
- Untouched password requirements are neutral. Show success/failure only after
  interaction or submit.
- Use correct autocomplete attributes and accessible inline errors.
- Before Stripe, show plan, price, amount due today, trial end/first charge date,
  auto-renewal, cancellation, and tax treatment.
- Stripe webhooks, not browser redirects, own entitlement transitions.
- Prevent duplicate customers, subscriptions, and charges with idempotency.
- Use the same navy/gold auth shell for sign-in, signup, OTP, and payment.

## 3. First login: workspace and project creation

The first authenticated screen welcomes the user and explains, visually and in
plain language:

- Private persistent 32 GB workspace on NAS-02 (storage, not RAM).
- The same workspace is available from Files, login nodes, compute jobs, and apps.
- Compute runs through the scheduler.
- Projects connect apps, collaborators, agents, and reproducible outputs.
- SciTeX works from desktop and mobile and supports user-created apps.

The primary action is **Create project**. Secondary actions are **Import project
or files** and **Use a guided sample**. The sample exists only after explicit
selection. Project creation shows name, location, and initial contents, then
lands inside that project. The chosen project persists across app navigation and
future sessions.

## 4. Shared shell and launcher

The floating launcher overlays content; it does not reserve a full-width bottom
strip. Apps use the full available viewport.

- Idle launcher is semi-transparent so users perceive content behind it.
- It becomes opaque on hover, focus-within, touch/press, expansion, or open menu.
- It never changes dimensions or causes layout shift while changing opacity.
- An actionable control must never remain hidden behind it. Scroll the control
  clear, collapse/move the launcher, or temporarily hide it.
- Do not solve collisions with a permanent full-width spacer.
- Respect safe-area insets, dynamic viewport height, keyboard focus, 200% zoom,
  `prefers-reduced-motion`, and 44 px targets.
- Automated geometry tests assert zero intersection between focused actionable
  elements and the launcher.

## 5. Project-connected leaf apps

### Scholar

- Canonical project picker is always visible and displays user-facing project
  names, never internal `MASTER/` paths.
- NAS-03 local Crossref/OpenAlex search is the primary path.
- Saving a result writes canonical user-library metadata under the user Scholar
  library and creates the project-local Scholar link/reference.
- PDF acquisition is an explicit user preference with storage consequences
  explained; availability and licensing remain honest.
- Library/search labels distinguish all libraries, current project, and search
  scope precisely.

### Stats

- Project-default mode lists only authorized CSV/TSV files from the active
  project, imports one, and saves configuration, results, plots, and provenance
  back to that project.
- **Quick analysis** is an explicit stateless alternative.
- Header, version, project selector, mobile behavior, and error states come from
  shared contracts.

### FigRecipe

- Never auto-select an unrelated example project.
- Project data, figure source, recipe, and exported artifacts remain connected.
- Deliver Data CRUD, X/Y assignment and table highlighting, category-to-variant
  plot chooser, hit-map selection, canvas pan/fit/reset, and light/dark grid.

### Writer

- Uses the same active project and canonical selector.
- Files, editor, compilation logs, and PDF are project artifacts.
- Desktop and mobile use the one compile path and one document state.

### Agents

Replace the production placeholder with a safe, useful SAC-backed MVP:

- Authorized inventory with name, project, lifecycle state, engine/model, safe
  last-seen, and details.
- Start/stop/open actions map one-to-one to named SAC commands and appear only
  when authorized.
- No raw token, environment, host-internal endpoint, or another user's agent.
- Loading, empty, denied, unavailable, and retry states are distinct.

### Cards

Replace the production placeholder with a project-scoped board MVP:

- Current project, canonical picker, authorized cards only.
- Create/open/edit/status/assign/archive and accessible non-drag alternatives.
- Search and status/assignee filters.
- Server-side tenant isolation; ordinary users never see fleet/global cards.

## 6. Chat

### Guaranteed first experience

Every email-verified real user receives **10 SciTeX-funded messages per day** on
the lowest-cost model that passes a basic usefulness/latency gate.

- Show selected model, remaining messages, and reset time before sending.
- Enforce quota atomically on stable user identity; concurrent sends cannot
  bypass it.
- Idempotent retry does not consume or bill twice.
- Provide operator global/provider spend caps and a kill switch.
- At the limit, preserve the draft and offer BYOK/provider setup or paid usage.
- Never silently change provider/model.

### Error contract

Never render raw LiteLLM/provider exceptions. Normalize and sanitize at least:

- insufficient provider balance;
- workspace/user quota reached;
- provider authentication failure;
- rate limit with retry time;
- unavailable/unauthorized/deprecated model;
- timeout;
- provider overload/outage.

Each state identifies whether the user, workspace admin, SciTeX, or provider must
act; preserves the failed prompt; offers one primary action; and exposes only a
sanitized support ID under technical details.

## 7. Settings

### Information architecture

On mobile, use cascading category → subcategory → settings navigation. Desktop
keeps the sidebar but every route, heading, active item, and browser title must
agree.

### Public profile and privacy

- A dedicated public-profile editor owns avatar, display name, username, bio,
  affiliation, ORCID, website, preview, save, and discard.
- Profile completion is optional during onboarding with **Skip for now** and
  **Do not show again**; it remains editable in Settings.
- Account email is private by default and omitted server-side from public APIs.
  Only a verified, explicitly selected email can be made public.

### AI providers and external clients

- Recommend supported low-cost connections such as DeepSeek based on measured
  capability/cost, not unexplained ranking.
- Distinguish providers from clients. Codex and local Claude Code are external
  clients that may call SciTeX MCP/API using the user's own local account/process.
- SciTeX provides OAuth-scoped remote MCP/API and compute integration; it does
  not proxy or share the user's Anthropic credentials.
- Provider secrets are masked, encrypted, never redisplayed, redacted from logs,
  testable before save, rotatable, and revocable.

### AI usage

- Use shared brand and SDK components.
- Show period, provider/account scope, estimated cost, requests, input/output
  tokens, meaningful empty states, usage freshness, limits, and save status.
- Browser title and page must agree; do not inherit an unrelated project title.

### MCP tools

- Separate servers → groups → individual tools.
- Show discovered, enabled, authorized, available, degraded, and paid counts.
- Support authenticated Streamable HTTP servers and stateless remote tools.
- Per-tool metadata includes provider, scopes, data access, side effects,
  billing class, expected latency, health, and rate/price.
- Lightweight tools may be free with abuse limits. Expensive tools require a
  machine-readable quote, explicit authorization/budget, idempotent execution,
  durable metering, cancellation, and a receipt.

### SSH and workspace

- Show stable Linux username and technical UID/GID details.
- Show canonical login endpoint, copyable command, and host-key fingerprints.
- State that compute access is scheduler-controlled and public direct compute SSH
  is disabled unless explicitly brokered.
- Show NAS-02 workspace path, 32 GB usage/quota, availability on login/compute,
  persistence, backup policy, and scratch distinction.
- Accept public keys only; detect/reject private keys without storing/logging the
  pasted material. Show key label, SHA-256 fingerprint, scope, created/last-used,
  expiry, rotation/revocation, propagation, and audit history.

### Billing

- Replace the placeholder with Stripe-backed plan, subscription, payment method,
  usage, spend controls, and invoices.
- Separate subscription allowance from metered API/AI/MCP/compute usage.
- Billing state is server-authoritative, webhook-driven, tenant-bound,
  idempotent, reconcilable, and auditable.
- Display current plan/status, renewal, amount, tax, payment summary, allowance,
  pending/final usage, invoice/receipt links, and failed-payment recovery.

### Workspace/Git synchronization

Rename the vague customer-facing **Project Health** concept to an exact technical
label such as **Workspace ↔ Git synchronization** or **Workspace/Gitea
consistency**. It is primarily an operator/developer diagnostic and should not
burden ordinary users. Normal synchronization is automatic. Surface it only
when action is genuinely required, with exact local/project/repository states,
last checked time, safe preview, conflict policy, and a precise repair action.

Large-file handling requires a separate architecture decision: evaluate Git LFS
versus content-defined chunking/deduplication, object storage, integrity,
garbage collection, partial upload/resume, encryption/tenant isolation, Gitea
integration, client compatibility, and migration. Do not hide that work behind
"Sync Project."

## 8. Docs, tours, and bilingual videos

App first use may offer **Watch tour**, **Later**, and **Do not show again**.
These preferences are account-level and reversible in Settings.

The existing scenario-driven video pipeline is the SSOT:

- One semantic action script drives the real browser.
- Stable IDs/data attributes, not translated labels, locate controls.
- Record both EN and JA UI locales from the same action timeline.
- Generate JA and EN narration and WebVTT subtitles as separate tracks.
- The player can switch audio/subtitle language without losing position.
- If UI language differs, offer matching UI+audio recordings as alternate video
  renditions while retaining synchronized chapter markers.
- Produce desktop first, then 390 px where the app supports the flow.
- CI detects missing selectors and visual drift; publishing requires human watch
  of both languages.
- Tutorials are versioned against app/Hub release and marked stale when key UI
  contracts change.

A dedicated video agent owns scenarios, recording, narration, captioning,
artifact QA, catalog updates, and stale-video reports. It does not own product
behavior.

## 9. Collaboration invitations and referral growth

Use the same simple interaction pattern—a copyable URL and three clear steps—
for two strictly separate products.

### Invite a collaborator

- An authorized project owner creates an opaque, expiring invitation bound
  server-side to one project, one least-privilege role, and a redemption limit.
- A recipient signs in or creates and verifies their own SciTeX account, reviews
  the project and role, then explicitly accepts. Opening the link or completing
  signup does not silently join the project.
- The link never reveals project files or acts as a continuing credential.
- Every collaborator has an individual stable identity; no guest, shared, link,
  or laboratory execution identity is created.
- Revocation prevents future redemption. Existing membership, role changes, and
  ownership transfer remain separate audited operations.

### Refer a new SciTeX user

- A referral URL attributes acquisition and may award promotional usage credit;
  it never grants project membership or reveals the referrer's private data.
- State the reward, qualifying event, campaign dates, limits, refund/chargeback
  behavior, and terms before signup.
- A reward becomes eligible only after the new user verifies their account and
  completes the published qualifying event. Paid campaigns wait through the
  refund/chargeback window.
- Prevent duplicate rewards, self-referrals, scripted/disposable-account bursts,
  and obvious billing-identity reuse without rejecting legitimate colleagues
  merely because they share a university or company network.
- Record attribution, pending approval, issuance, denial, and reversal in an
  auditable reward ledger with per-user and campaign caps.

Collaboration invitations and referrals use different routes, token formats,
tables, redemption services, permissions, and copy. Neither token can be used
as login, API, password-reset, or project-content authorization.

## 10. Ownership matrix

| Owner | Responsibility |
| --- | --- |
| `scitex-hub` | Landing, auth/OTP, Stripe, first-login onboarding, stable identity/workspace integration, project context propagation, Chat allowance/error mapping, Settings assembly, production E2E and release |
| `scitex-ui` SDK | Navy/gold semantic tokens, app/auth/settings shell primitives, canonical project selector, launcher overlay/collision behavior, responsive navigation, first-use tour/player primitives |
| `scitex-app` SDK | Manifest/provider contracts, project-context API, app header/version slots, command/action declarations, authorization/fail-closed contracts |
| `scitex-scholar` | Local-first search, library/save/PDF preferences, Scholar project artifacts |
| `scitex-stats` | Project data import, analysis, outputs/provenance, Quick analysis |
| `figrecipe` | Data/plot/canvas workflow and project figure artifacts |
| `scitex-writer` | Project files, editor, compile/log/PDF workflow |
| `scitex-agent-container` | SAC inventory/lifecycle/authorization commands and stable machine identity; Agents GUI adapter stays separate when needed |
| `scitex-cards` | Project board domain and tenancy |
| Hub video agent | Bilingual scenario recordings, narration/subtitles, QA, publishing metadata |
| Hub product lead | Scope, cross-repo dependencies, artifact tracking, independent review, integration, release, live readback, and operator communication |

## 11. Delivery gates

No task is complete at assignment or visual mockup. Required lifecycle:

1. Scope and owning repo agreed.
2. Owner acknowledges with branch.
3. Implementation commit and focused tests.
4. PR with exact head SHA.
5. CI green.
6. Independent behavioral/security/accessibility review.
7. Merge in owning repo.
8. Leaf release when Hub consumes a package.
9. Hub integration and pin/floor update.
10. Real desktop browser journey from `scitex.ai` sign-in to compiled output.
11. Production live readback with project/files/identity/usage evidence.
12. 390 px pass after desktop coherence.

## Private Beta exit criterion

A newly verified user, without staff intervention and without adding a personal
AI provider, can create a project, receive a useful Chat response, save a paper,
analyze project data, create a figure, compile a manuscript PDF, log out, return,
and find the same project and outputs. No step exposes internal paths, raw
provider errors, another user's data, dead placeholders, or an unexplained
billing surprise.
