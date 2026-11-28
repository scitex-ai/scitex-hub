# Billing accounts a lab or organisation can pay for (design note)

Status: design only, not implemented. Operator decision 2026-11-27 (a): *a lab/organisation can pay for its
members' usage.* The catalog states it (`pricing.json` `billing_policy.payers: ["individual", "organization"]`);
this note is the minimal data model for wiring it up. Tracking issue: scitex-ai/scitex-hub#1255.

## Today

Every billing table is keyed by `User`: `PlanSubscription`, `SpendControl`, `SpendAlert`, `BillingAccountState`,
`BillingAccountEvent`, `WorkloadSession`. Usage is rated per user (`UsageSource.snapshot(user, ...)`), the cap is
per user, dunning restricts a user. `organizations_app` already has `Organization` / `OrganizationMembership`
(roles) and `ResearchGroup` / `ResearchGroupMembership` (a lab inside an organisation).

## Model

Introduce one payer entity, so "who pays" stops being "the user":

```
BillingAccount
  id
  kind            individual | organization        (catalog: billing_policy.payers)
  owner_user      FK User, null                    kind=individual
  organization    FK Organization, null            kind=organization (a lab = a ResearchGroup's organisation, or the group itself; see Q1)
  provider_customer_id                             one Stripe customer per payer
  currency        USD                              billing_policy.currency_of_record
  created_at

BillingAccountMember                               who may draw on an organisation account
  account         FK BillingAccount (kind=organization)
  user            FK User
  monthly_cap_usd decimal, null                    per-member sub-cap set by the org admin; null = no sub-cap
  active_from / active_until                       membership is dated so a usage event resolves to ONE payer
  approved_by     FK User                          an org admin (OrganizationMembership.role in admin/owner)
```

Every user gets an `individual` account lazily (backfill migration: one per existing user, carrying their
`PlanSubscription` / `SpendControl` / `BillingAccountState`). The per-user tables gain a `billing_account` FK; the
`user` FK stays as "who did it" for audit, `billing_account` becomes "who pays".

## Resolution rule

A usage event (workload, storage, egress, external service) is charged to exactly one account:

1. the project's sponsoring organisation account, if the project belongs to an organisation with an account and
   the user is an active `BillingAccountMember` at the event time;
2. otherwise the user's individual account.

One function owns this (`spend_app.services.payer.resolve(user, project, at)`), and the ledger (#1232) stores the
resolved `billing_account_id` on every rated event so later membership changes never re-attribute past usage.

## Caps, alerts, dunning

- The organisation account has its own monthly cap (`SpendControl` keyed by account). A member's draw is limited by
  `min(member sub-cap, org remaining)`; the gate (`gate.require`) checks the resolved payer, not the user.
- Alerts go to the org admins for the org cap and to the member for their sub-cap.
- A restricted org account blocks new compute on org projects only; the member's personal projects follow their
  individual account. Never deletes data (same rule as today).

## Credits

Plan grants and prepaid top-ups (API-billing decision, 2026-11-27) belong to the account, not the user, so an
organisation can buy a top-up that its members draw down.

## Open questions for the operator

- Q1: is "lab" an `Organization` or a `ResearchGroup`? (Proposal: allow both kinds of owner; a ResearchGroup account
  is paid by its lead.)
- Q2: does an organisation pay for members' plan fees (seats), or only metered usage beyond each member's own plan?
- Q3: invoicing: one monthly invoice per organisation with a per-member breakdown (proposal), or per-member invoices?
- Q4: can an organisation account be used by non-members invited to one project (guest sponsorship)?

## Not in scope here

Public anonymous-download egress paid by SciTeX (decision c) is a separate payer (SciTeX itself) and needs the egress
collector first; see scitex-ai/scitex-hub#1256.
