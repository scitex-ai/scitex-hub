# Academic discount — eligibility, appeal, and reviewer practice

Status: implemented on `feat/academic-discount-registration-billing-20261019`
(operator CCT4555 lane + CCT4558 appeal add-on). Lane card:
`hub-academic-discount-registration-billing-20261019`.

## Why this exists

Cloud Pro has two prices for the same product: $39/mo general,
$19/mo academic (`subscription-general` vs `subscription-student` in
`apps/infra/public_app/data/pricing.json`). The 50%-off is the ROW, not a
coupon applied at the provider — there is no coupon plumbing at Stripe, and
the `ACADEMIC50` landing-table code path stays `coming_soon` (a different
door, still unwired).

Two gates stand between a signup and the wrong price: the automatic checker
(which misses), and the human appeal (which catches the miss).

## The automatic check

One definition, in `apps/infra/accounts_app/academic.py`:
`is_japanese_academic_email` + `JAPANESE_ACADEMIC_DOMAINS` (`.ac.jp`
institutions plus the listed `.go.jp` research institutes).
`apps/infra/auth_app/models.py` and `apps/infra/accounts_app/models/profile.py`
re-export it — a second copy is how the old flags drifted apart, so there is
exactly one.

The worldwide `swot`-based checker lives only on branch
`feature/lp-beta-polish`, never merged, deliberately not ported (new
dependency + worldwide-eligibility decision not made). If it lands, it lands
behind this module's interface.

The evaluation point is verification, never the form: `mark_verified`
(email signup) and `begin_social_signup` (provider-verified address) call
`grant_academic_discount(user, proven_email)`. The grant is a durable 1:1
`UserDiscount` row (code `ACADEMIC50`); the funnel selector
(`funnel_plan` rule 2) reads the ROW, never the raw email, and places a
grant-holding account still on the funnel default onto `subscription-student`.
An explicit `?plan=` or a recorded non-free plan always wins. Stripe needs
nothing new: the row flows through plan-bound sessions, metadata-carried
`pricing_id`, and provider-confirmed activation — chargeable iff
`SCITEX_HUB_STRIPE_PRICE_SUBSCRIPTION_STUDENT` is configured.

Grant-only, idempotent: re-verification converges on one row; losing the
address does not auto-revoke (the subscription already exists at the
provider — silent revocation would reprice a paying account).

## The appeal (auto-check misses)

Route: `/accounts/settings/discount-appeal/` (signed in only), linked from
the payment step whenever a full price is quoted without a grant.
One open appeal per account (form refusal + partial unique constraint
`unique_open_discount_appeal_per_user` against the double-click race).
History stays visible to the requester, including the reviewer's note.

## Reviewer best practice

Queue: Django admin → Discount Appeals (open first). For each appeal:

1. **Verify the affiliation, not the address.** A staff page, personnel
   listing, or lab page naming the requester is ideal; the `evidence` field
   should point at one. The claimed address failing the checker is EXPECTED
   (that is why there is an appeal) — do not reject for that.
2. **Approve** (`approve_appeals` action) only when the affiliation checks
   out. Approval issues the grant linked to the appeal, so the audit trail
   answers "why does this account pay $19". A revoked grant is never
   resurrected by approval — un-revoke explicitly first.
3. **Reject** with a note the requester can read (write `reviewer_note` on
   the row, then the action). "Not an academic institution" and "could not
   verify — resubmit with a staff page link" are both fine; silence is not.
4. **Never edit the requester's claim.** If the institution name is wrong,
   reject with a correction note and let them re-file — the row is their
   statement, your note is yours.
5. **New institution missing from the checker?** Approve the appeal AND file
   the domain for the checker list — the appeal is the signal the list is
   incomplete. The list change is a separate commit, never bundled with a
   customer decision.

## Invariants

* Eligibility is a durable row, never a per-request email guess.
* The grant never chooses a plan; the selector never mints eligibility.
  The appeal approval is the one place the two meet, through
  `grant_approved_appeal`, audited.
* No file uploads on the appeal form (malware drop); no PAN/CVC anywhere
  near it (unchanged funnel rule).
* Prices live in `pricing.json`; this lane adds no price, only the mapping
  from account to row.
