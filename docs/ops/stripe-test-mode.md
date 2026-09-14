# Stripe test-mode setup + demo script

Goal: the paid journey (sign up, add card, trial, choose plan, cancel) works in
Stripe TEST mode the moment keys are added. No real money moves in test mode.

Code map:

| Piece | Where |
|---|---|
| Provider interface (views only use this) | `apps/infra/public_app/services/billing_provider.py` |
| Stripe implementation | `apps/infra/public_app/services/stripe_provider.py` |
| Card setup (Checkout, `mode="setup"`) | `apps/infra/public_app/services/stripe_setup.py` |
| Endpoints | `apps/infra/public_app/views/billing.py`, `urls/pages.py` |
| Billing page | `/accounts/settings/billing/` (`accounts_app/views/billing_views.py`) |
| Catalog bootstrap | `python manage.py stripe_bootstrap_test` |
| Prices (SSOT, USD, tax included) | `apps/infra/public_app/data/pricing.json` |

## 1. Environment variables

| Variable | Required | Value |
|---|---|---|
| `SCITEX_HUB_STRIPE_SECRET_KEY` | yes | `sk_test_...` (Dashboard > Developers > API keys, **Test mode** toggle on) |
| `SCITEX_HUB_STRIPE_WEBHOOK_SECRET` | yes | `whsec_...` from `stripe listen` (dev, section 4) or the Dashboard endpoint (public hosts) |
| `SCITEX_HUB_STRIPE_PRICE_SUBSCRIPTION_STUDENT` | for plan selection | `price_...` printed by the bootstrap command |
| `SCITEX_HUB_STRIPE_PRICE_SUBSCRIPTION_GENERAL` | for plan selection | `price_...` printed by the bootstrap command |
| `SCITEX_HUB_BILLING_PROVIDER` | no | `stripe` (default) |

No publishable key (`pk_test_...`) is needed: card entry happens on
Stripe-hosted pages (Checkout and the Customer Portal), reached by server-side
redirects, so no Stripe.js runs on our pages.

Put the values in `SECRET/.env.dev` (never commit them), then recreate the
Django container so settings reload.

Without keys, nothing breaks: signup works and lands on the profile page, and
the billing page says "Card registration opens soon".

## 2. Get test keys

1. Sign in at <https://dashboard.stripe.com>, switch **Test mode** on (top right).
2. Developers > API keys > reveal the **Secret key** (`sk_test_...`).
   A restricted key (`rk_test_...`) also works if it has write access to
   Customers, Checkout Sessions, SetupIntents, Payment Methods, Products,
   Prices, Subscriptions and Billing Portal Sessions.

## 3. Create products and prices

```bash
docker exec -it scitex-hub-dev-django-1 python manage.py stripe_bootstrap_test
```

It reads the subscription rows of `pricing.json` (Cloud Academic $19/mo, Cloud
Standard $39/mo), creates or finds them in Stripe (product id
`scitex-<pricing id>`, price `lookup_key` includes the amount, `tax_behavior`
inclusive) and prints only the `SCITEX_HUB_STRIPE_PRICE_*=price_...` lines.
Re-running creates nothing new. It refuses a live key unless given `--live`.

Currency: every price is created with `currency="usd"` explicitly, so it works
on the "SciTeX Inc. sandbox" account whose default currency is JPY. Stripe
charges the card in USD and settles to the JPY balance with conversion (Stripe
shows the conversion fee in the balance transaction). Customers are billed in
USD, matching `/tokushoho/`.

## 4. Webhook

Endpoint path: `/billing/webhook/stripe/`

Events to send:

- `checkout.session.completed` (marks the card usable; required)
- `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted` (mirror plan status; required)
- `setup_intent.succeeded`, `invoice.paid`, `invoice.payment_failed` (recorded in `BillingEvent` for audit; plan status follows from the subscription events)

The endpoint needs no login and no CSRF token (it is `csrf_exempt`; the
signature is its only authentication), and no middleware redirects it.

### Dev (behind Cloudflare Access): Stripe CLI forwarding

Stripe cannot reach a URL behind Cloudflare Access, so dev receives events
through `stripe listen`, which opens an outbound connection to Stripe and
replays events locally. Dev runs it as the `scitex-hub-dev-stripe-listen`
sidecar, sharing the Django container's network namespace:

```bash
stripe listen \
  --forward-to http://127.0.0.1:8000/billing/webhook/stripe/ \
  --headers "Host: compute-03-net.scitex.ai"
```

- `--headers Host:` makes the forwarded request pass `ALLOWED_HOSTS`.
- The CLI authenticates with the test secret key (`--api-key sk_test_...` or
  `STRIPE_API_KEY` env); `stripe listen --print-secret` prints the `whsec_...`
  to put in `SCITEX_HUB_STRIPE_WEBHOOK_SECRET`. It normally survives sidecar
  restarts; if deliveries start returning 400 `invalid_signature`, print it
  again and update the env.
- By default it forwards every event, which includes all those listed above.
- Run it on compute-03 directly the same way if the sidecar is not running;
  point `--forward-to` at the Django port published on that host.
- Watch deliveries in the sidecar log: `docker logs -f scitex-hub-dev-stripe-listen`
  (each line shows the event type and our HTTP status; 200 is success).

### Prod or any publicly reachable host: Dashboard endpoint

Dashboard > Developers > Webhooks > Add endpoint >
`https://<host>/billing/webhook/stripe/`, select the events above, then copy
the endpoint's signing secret. Make sure no Access policy or WAF challenge sits
in front of `POST /billing/webhook/stripe/`.

## 5. Customer Portal (change card, change plan, invoices)

Test mode: Settings > Billing > Customer portal > **Save** once (the portal
needs a saved configuration). Enable: update payment method, cancel at period
end, switch plans (add both SciTeX Cloud products), invoice history.

## 6. Test cards

| Card | Behaviour |
|---|---|
| `4242 4242 4242 4242` | succeeds, no authentication |
| `4000 0025 0000 3155` | requires 3D Secure at setup; later off-session charges succeed |
| `4000 0000 0000 9995` | declined (insufficient funds), to show the failure path |

Any future expiry, any 3-digit CVC, any postal code.

## 7. Demo script (click path)

1. Open `https://compute-03-net.scitex.ai/auth/signup/`. Point at the copy:
   "card required, no charge during the trial". Sign up with a fresh email and enter the emailed code.
2. You land on **Settings > Billing** with the welcome banner, and the Trial
   card shows the trial end date (registration + 30 days).
3. Click **Add card**. Stripe Checkout opens (setup mode, no amount). Enter
   `4000 0025 0000 3155`, complete the 3D Secure test page.
4. Back on Billing, the card shows `visa •••• 3155  Verified` (refresh once if
   the webhook is a second behind).
5. In **Plan**, click **SciTeX Cloud Standard — $39/mo**. The plan shows
   `active` with a renewal date; in the Stripe Dashboard the subscription
   starts at the registration date (backdated, per the 特商法 page) and the
   first invoice is paid.
6. Click **Open billing portal** to show invoices and card change, then return.
7. Click **Cancel plan**. The plan shows "Ends on …; it will not renew"
   (cancel at period end, no proration, matching 特商法).
8. Optional: in the Dashboard, cancel the subscription immediately; the
   `customer.subscription.deleted` webhook flips the plan off on refresh.

## 8. Known gaps (not in this change)

- Card data retention after an unconverted trial (特商法: discard after 7 days)
  is not automated; detach payment methods manually for now.
- "One trial per email or card" is not enforced (needs card fingerprint check).
- No automatic Japanese consumption-tax breakdown on invoices: Stripe Tax is
  not enabled and the 適格請求書 registration number is not on invoices.
- The legacy staff-only `billing/checkout/` uses `SCITEX_HUB_BILLING_PLANS`
  (JPY); do not set that variable, it would replace the USD table on /tokushoho/.
