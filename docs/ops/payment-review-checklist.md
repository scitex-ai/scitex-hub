# Payment-processor review checklist

What a card-processor review (Stripe, PAY.JP, KOMOJU, card-brand underwriting)
typically checks, mapped to the pages SciTeX actually serves. Audited from the
templates on 2026-09-14. ✓ = ready, ✗ = gap to fix before (re)applying.

Stripe rejected a previous application, so treat every ✗ as a possible reason.

## 1. Legal entity and 特定商取引法 page

| Check | Page | Status |
|---|---|---|
| Seller legal name (販売業者) | `/tokushoho/` 株式会社ＳｃｉＴｅＸ | ✓ |
| Responsible person (運営統括責任者) | `/tokushoho/` | ✓ |
| Registered address, byte-identical to 国税庁 record | `/tokushoho/` (settings_commerce.py) | ✓ |
| Phone number | `/tokushoho/` | ✓ |
| Readable email (not Cloudflare-obfuscated) | `/tokushoho/` `info@scitex.ai` | ✓ |
| Price, extra fees, payment method, payment timing, delivery timing, cancellation | `/tokushoho/` | ✓ |
| English version for the reviewer | `/tokushoho-en/` | ✓ |
| Payment-method row states card payment starts "after Stripe's review" | `/tokushoho/` 支払方法 | ✓ now; ✗ must be reworded the day card payment opens |
| Company name and address in Terms "Contact Us" | `/terms/#contact-us` says only "SciTeX", no address; its comment still says "not incorporated until 2026-08-08" | ✗ add 株式会社ＳｃｉＴｅＸ + registered address from settings |

## 2. Clear pricing and currency

| Check | Page | Status |
|---|---|---|
| Prices published with currency | `/pricing/`, `/tokushoho/` (USD) | ✓ |
| Tax-inclusive display (総額表示) | `/pricing/`, `/tokushoho/` "価格はすべて税込" | ✓ |
| Billing currency stated | `/tokushoho/` "実際の請求はUSDで行われます" + JPY reference column | ✓ |
| Prices in Stripe match the site | `manage.py stripe_bootstrap_test` creates prices from pricing.json | ✓ |
| Accepted card brands | `/terms/` lists Visa, Mastercard, Amex, Discover; JCB (the main Japanese brand) missing | ✗ list JCB (and Diners) or drop the list |
| "From" prices for services are not buyable online | `/services/` quote flow, not a checkout | ✓ |

## 3. Refund and cancellation policy

| Check | Page | Status |
|---|---|---|
| Trial, first charge, renewal, no proration | `/tokushoho/` 支払時期, 返品・キャンセル | ✓ |
| Terms agree with 特商法 on the trial | `/terms/#free-trial`: "automatically charged at the end of the free trial unless you cancel". `/tokushoho/`: nothing is charged unless the customer chooses to continue (then billed from registration). | ✗ contradiction; rewrite Terms to the 特商法 model (the code implements the 特商法 model) |
| Cancel from the account | `/terms/#cancellation` + Settings > Billing **Cancel plan** | ✓ (live once keys are set) |
| Data/card retention after an unconverted trial (discard after 7 days) | stated on `/tokushoho/` | ✗ not automated in code; automate or run manually and say so internally |
| One trial per email or card | stated on `/tokushoho/` | ✗ not enforced in code |

## 4. Terms and privacy

| Check | Page | Status |
|---|---|---|
| Terms of Use reachable from every page | footer → `/terms/` | ✓ |
| Terms accepted at signup | `/auth/signup/` agree_terms checkbox | ✓ |
| Governing law / venue (日本法, 静岡地方裁判所) | `/terms/` | ✓ |
| Terms "Last Updated" is current | `/terms/` January 22, 2026 (before incorporation and the trial model) | ✗ update after the fixes above |
| Privacy policy reachable | footer → `/privacy/` | ✓ |
| Names the payment processor and cross-border transfer (個人情報保護法 外国にある第三者への提供: Stripe, US) | `/privacy/` says only "our payment processors" | ✗ name Stripe, its country, and the transfer basis |
| No "share with third parties for marketing" clause | `/privacy/` has one ("with your consent ... for marketing purposes") | ✗ remove unless it is real |
| Privacy "Last Updated" is current | `/privacy/` January 29, 2026 | ✗ |

## 5. Reachable contact

| Check | Page | Status |
|---|---|---|
| Contact page | `/contact/` with inquiry form | ✓ |
| Every address shown delivers | `/contact/` shows `sales@scitex.ai` and `hello@scitex.ai`; only `info@scitex.ai` is operator-confirmed | ✗ send a test mail to each or show only `info@` |
| Phone reachable in business hours | `/tokushoho/` | ✓ (make sure it is answered during review) |

## 6. Working product demo

| Check | Page | Status |
|---|---|---|
| Public site explains the product | `/`, `/pricing/`, `/services/`, `/demos/` | ✓ |
| Signup works end to end | `/auth/signup/` → email code → account | ✓ |
| Card registration and plan selection work | Settings > Billing (this change) | ✓ in test mode once keys are set; ✗ until then the page says "Card registration opens soon" |
| Reviewer can see the paid flow | demo script `docs/ops/stripe-test-mode.md` | ✗ prepare a reviewer account and a short screen recording of the test-mode flow |

## 7. No prohibited-business signals

| Check | Page | Status |
|---|---|---|
| No crypto, gambling, adult, investment content | template search found none | ✓ |
| Donations on a for-profit company | `/donate/` ("Support SciTeX" in the footer) asks for monthly donations and says Stripe donations are "pending the Stripe Japan application" | ✗ high risk: processors restrict donations to for-profits. Remove the page from the footer and drop the Stripe sentence before applying, or reframe as GitHub Sponsors only |
| Marketplace / facilitating third-party sales | `legal/marketplace_terms.html` (no URL routes to it) covers free open-source app submission only, no paid resale | ✓ (say "no third-party payments" if asked) |
| Metered compute resale | `/pricing/` rate card marked "Coming soon" | ✓ (not billed yet; explain if asked) |
| Site identity consistent (brand, domain, email domain) | scitex.ai everywhere | ✓ |

## Before reapplying

1. Fix the Terms trial clause, contact block, card brands and date.
2. Update the privacy policy (Stripe named, cross-border transfer, no marketing sharing).
3. Remove or rework `/donate/`.
4. Verify every email on `/contact/`.
5. Run the test-mode demo (docs/ops/stripe-test-mode.md) and keep a recording.

## Provider portability

Billing views call only `get_billing_provider()`
(`apps/infra/public_app/services/billing_provider.py`). Adding PAY.JP or
KOMOJU means one new class implementing `BillingProvider` and one entry in
`PROVIDER_FACTORIES`, selected with `SCITEX_HUB_BILLING_PROVIDER`; no view or
template change. The 特商法 支払方法 row must then name that processor.
