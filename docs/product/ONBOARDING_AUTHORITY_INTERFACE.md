# The onboarding authority — interface contract

Status: implemented in `fix/signup-payment-funnel-review-20260917` (follow-up to
PR #934). Owner of the payment half: `scitex-hub-payment-gui`. Consumer of the
auth half: `scitex-hub-auth-gui`.

## Why this exists

The signup funnel has two doors — email/OTP (`apps/infra/auth_app/api_views.py`)
and social (`apps/infra/auth_app/adapters.py`) — and before PR #934's review they
had **two different opinions** about what a new account must do next. The OTP
path activated and logged the account in and then deleted the only record that it
was mid-signup; the social path redirected to `/` and never consulted the
redirect policy at all. Nothing downstream could tell a half-finished signup from
a finished one, so every product route was reachable without a payment method.

There is now ONE durable, typed authority that both doors write and that the
product gate reads. This document is the wire between the two workstreams: if you
own signup/OTP/social, these are the only functions you call.

## The interface

`apps/infra/auth_app/onboarding.py` — no behaviour lives in the views.

| Function | When the AUTH side calls it | Effect |
| --- | --- | --- |
| `mark_verified(user, source="email")` | the OTP is accepted (email signup complete) | deletes `PendingSignup`, creates/keeps `OnboardingState(step=PAYMENT)` |
| `begin_social_signup(user, provider)` | a provider-verified social account is created | creates `OnboardingState(step=PAYMENT, source=<provider>)` |
| `begin_signup(user, email, source)` | the signup FORM was submitted | no-op (documented; see below) |
| `next_url(user)` | any redirect after signup/login | the payment step while payment is owed, else `LOGIN_REDIRECT_URL` |
| `state_for(user)` / `step_for(user)` | when you need to know the account's step | the row, or `None` outside the funnel |
| `payment_required(user)` | the product gate's single question | `step == PAYMENT` **and** the deployment can take a card |

The PAYMENT → PRODUCT transition is written by `mark_activated(user,
pricing_id=…)`, which the **payment** side calls from provider-confirmed webhook
state only. The auth side must not call it, and must not advance the step from a
browser redirect: the success URL is a claim made by the browser.

## Invariants the auth side can rely on

1. **`None` is a real answer.** An account with no `OnboardingState` is not in the
   funnel: operator-created, migrated and pre-funnel accounts are never gated and
   `next_url` returns the ordinary post-login destination for them.
2. **Every call is idempotent.** `mark_verified` / `begin_social_signup` are
   `get_or_create` on a `OneToOne`; a double-submitted verify, a replayed allauth
   callback or a second login cannot create a second row or reset a row that has
   already reached PRODUCT.
3. **`mark_verified` is NOT for email changes.** An active account re-proving a
   new address is not signing up; enrolling it would gate an established account
   behind a payment step it already passed. The OTP handler keeps that branch
   separate (it deletes any stale `PendingSignup` and nothing else).
4. **`mark_verified` deletes `PendingSignup` in the same transaction.** A marker
   that outlives the signup would let a later administrator deactivation be
   undone by the verify path (the PR #775 bypass).
5. **Nothing here reads a card.** Entitlement is never inferred from
   `PaymentMethod`: a saved card without a provider-confirmed subscription is
   still `PAYMENT` (the payment step renders its `processing` state).

## What the auth side must NOT do

- Do not write `OnboardingState` directly, and do not compare `step` strings
  against literals — use `onboarding.Step` / `PAYMENT` / `PRODUCT`.
- Do not add a second redirect rule for a verified signup. Call `next_url(user)`
  (or `billing_provider.post_signup_redirect_url`, which delegates to it).
- Do not gate anything in the auth app: the product gate is
  `apps.infra.accounts_app.middleware.OnboardingGateMiddleware`, driven by
  `payment_required`, and its path classification lives in
  `apps/infra/accounts_app/funnel.py`.

## The product gate, in one paragraph

An authenticated, non-staff request whose `payment_required` is true is
classified by `funnel.request_is_gated`: everything except an explicit list of
exempt mounts (`/accounts/`, `/auth/`, `/billing/`, `/admin/`, `/healthz/`,
`/i18n/`, `/static/`, `/media/`, the legal/marketing pages and the PWA/robot
files) is refused — a redirect to the payment step for a browser, a `402` JSON
body for `/api/` and `/platform/api/`. It is fail-closed on purpose: a deny-list
of "product" paths is re-derived every time a mount is added, and the one that is
forgotten is the bypass. A test reads `config/urls.py` and fails when a top-level
mount is on neither side of the classification, so a new mount is a decision
somebody makes rather than a hole somebody leaves.

**The one documented exception:** when no billing provider is configured, NO
account can enter a card, so demanding one would lock every new signup out of the
product forever. The requirement is therefore *suspended* (the step still says
activation is waiting) rather than *faked*. `deployment_can_take_a_payment()` is
the single place that decides this; a test pins both branches.
