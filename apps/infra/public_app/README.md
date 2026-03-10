# public_app - Public-Facing SaaS Gateway & Subscription Management

## Purpose

**public_app** is the public-facing layer of the SciTeX platform, providing landing pages, user authentication, subscription/billing management, donation processing, and API key provisioning. It serves as the SaaS gateway for the entire platform, handling all user onboarding, pricing presentation, and account-level features.

## One-Line Summary

Public-facing SaaS layer providing landing pages, subscription management, donation processing, user authentication, and API key provisioning.

## Key Responsibilities

### 1. **Public Landing & Marketing**
- Main landing page with SciTeX ecosystem overview (Scholar, Writer, Code, Viz modules)
- Vision and values page
- Publications and research highlights
- Demo and tutorial pages
- Contributor and team information
- Blog and news content

### 2. **Subscription & Pricing Management**
- Individual pricing tiers: Free, Standard, Professional, Researcher Plus
- Institutional plans: Lab License, Department, University Enterprise
- Japanese market offerings: Pilot Program, MEXT Partnership
- Add-on services: Custom prompts, on-premise setup, training, consultation
- Dynamic pricing based on subscription plan
- Feature flag management per subscription tier

### 3. **User Authentication & Account Management**
- User signup and registration with email validation
- Login with username/email support and "remember me" option
- Password reset and recovery workflow
- Email verification via OTP (one-time password)
- Logout and session management
- Account creation and initial profile setup

### 4. **Donation & Fundraising**
- Donation processing with multiple payment methods (credit card, PayPal, GitHub Sponsors)
- Donation tier management and recognition
- Email verification for donation confirmation
- Fundraising campaign tracking ($75K annual goal)
- Public donation history (anonymized)
- Donation success confirmation flow

### 5. **API Key & Programmatic Access**
- API key generation and management
- API key permissions (read, write, delete)
- Rate limiting configuration per key
- Key expiration and lifecycle management
- Prefix-based key identification

### 6. **Service Integrations**
- Integration with external services:
  - ORCID (researcher profile)
  - GitHub (code repositories)
  - GitLab (alternative code repositories)
  - Zenodo (open science repository)
  - Figshare (research data sharing)
  - Mendeley (reference management)
  - Zotero (reference management)
- OAuth token management for integrations
- Token refresh and synchronization

### 7. **Legal & Compliance**
- Privacy policy page with GDPR/CCPA considerations
- Terms of use and service agreement
- Cookie policy and consent
- Contact and support information
- Legal compliance documentation

### 8. **API Documentation & Support**
- API documentation and reference
- Getting started guide
- Code examples and SDKs
- Support resources and FAQ

## Architecture

### Directory Structure

```
public_app/
├── models.py                  # Subscription, APIKey, ServiceIntegration, CloudResource models
├── admin.py                   # Django admin customization
├── apps.py                    # App configuration
├── urls.py                    # URL routing
├── views.py                   # All view functions (monolithic)
├── forms.py                   # Django forms for user input
│
├── templates/cloud_app/       # HTML templates
│   ├── landing.html           # Main landing page
│   ├── signin.html             # Login page
│   ├── signup.html            # Signup/registration page
│   ├── premium_subscription.html  # Pricing page
│   ├── donate.html            # Donation page
│   ├── legal/                 # Privacy, terms, cookie policy
│   └── pages/                 # Vision, publications, contributors, etc.
│
├── static/cloud_app/          # Static assets (CSS, JS, images)
├── migrations/                # Database migrations
└── tests.py                   # Test suite
```

### Models

#### SubscriptionPlan (~50 lines)
- **Purpose:** Define pricing tiers and feature availability
- **Fields:**
  - `name` (str): Plan name (Free, Standard, Professional, etc.)
  - `plan_type` (str): Individual or Institutional
  - `price_monthly` (decimal): Monthly subscription cost
  - `price_yearly` (decimal): Yearly subscription cost (with discount)
  - `max_projects` (int): Project limit per tier
  - `storage_gb` (float): Storage allocation in GB
  - `cpu_cores` (int): CPU cores for computation
  - `gpu_vram_gb` (float): GPU VRAM allocation
- **Feature Flags:**
  - `has_watermark` (bool): SciTeX watermark requirement
  - `requires_citation` (bool): Citation requirement
  - `requires_archive` (bool): Archive requirement
  - `has_priority_support` (bool): Priority support access
  - `has_custom_integrations` (bool): Custom integration support
  - `has_team_collaboration` (bool): Team collaboration features

#### Subscription (~70 lines)
- **Purpose:** User subscription instances tied to plans
- **Fields:**
  - `user` (FK to User): The subscriber
  - `plan` (FK to SubscriptionPlan): Selected plan
  - `status` (str): Active, Suspended, Cancelled, Expired
  - `stripe_subscription_id` (str): Stripe reference
  - `stripe_customer_id` (str): Stripe customer reference
  - `trial_start_date` (datetime): Trial period start
  - `trial_end_date` (datetime): Trial period end
  - `subscription_start_date` (datetime): Subscription period start
  - `subscription_end_date` (datetime): Subscription period end
- **Methods:**
  - `is_active()`: Check if subscription is currently valid

#### CloudResource (~40 lines)
- **Purpose:** Track usage metrics per subscription
- **Fields:**
  - `user` (FK): User consuming resource
  - `subscription` (FK): Associated subscription
  - `resource_type` (str): CPU, GPU, storage, bandwidth, api_calls
  - `amount_used` (float): Quantity consumed
  - `unit` (str): Unit of measurement (hours, GB, requests)
  - `period_start_date` (datetime): Billing period start
  - `period_end_date` (datetime): Billing period end
- **Use Case:** Quota enforcement and usage-based billing

#### APIKey (~50 lines)
- **Purpose:** Programmatic API access with fine-grained permissions
- **Fields:**
  - `user` (FK): API key owner
  - `name` (str): Human-readable key name
  - `key` (str): Hashed key value
  - `prefix` (str): Unhashed prefix for identification (e.g., "scitex_abc123...")
  - `can_read` (bool): Read permission
  - `can_write` (bool): Write permission
  - `can_delete` (bool): Delete permission
  - `rate_limit` (int): Requests per minute
  - `is_active` (bool): Enable/disable key
  - `expires_at` (datetime): Expiration timestamp
- **Methods:** Key validation and permission checking

#### ServiceIntegration (~50 lines)
- **Purpose:** Manage external service connections
- **Fields:**
  - `user` (FK): User who integrated service
  - `integration_type` (str): ORCID, GitHub, GitLab, Zenodo, Figshare, Mendeley, Zotero
  - `external_id` (str): User's ID on external service
  - `access_token` (str): OAuth access token
  - `refresh_token` (str): OAuth refresh token (if available)
  - `last_synced` (datetime): Last synchronization timestamp
- **Use Case:** OAuth token storage and refresh management

### Forms

#### DonationForm (~40 lines)
- Fields: Amount, payment method (card, PayPal, GitHub Sponsors)
- Validation: Minimum donation amount, valid payment method
- Purpose: Donation submission

#### EmailVerificationForm (~30 lines)
- Fields: Email address
- Generates and sends 6-digit OTP code
- Stores code in session for verification

#### VerifyCodeForm (~30 lines)
- Fields: OTP code
- Validates code and expiration
- Checks against session-stored code

#### SignupForm (~60 lines)
- Fields: Username, email, password, password confirmation
- Validation: Password matching, unique username/email
- Purpose: User registration

#### LoginForm (~40 lines)
- Fields: Username/email, password, remember me checkbox
- Purpose: Authentication

## Views Overview (758 lines total)

### Public Pages (~200 lines)
- `index()` - Main landing page with feature showcases
- `vision()` - SciTeX vision, values, and mission
- `publications()` - Research publications and citations
- `demo()` - Interactive demo page
- `contributors()` - Team members and contributors
- `api_docs()` - API documentation and reference

### Authentication Views (~150 lines)
- `signup()` - User registration with email validation
- `login_view()` - Authentication with remember me option
- `logout_view()` - Session cleanup
- `verify_email()` - Email verification via OTP
- `forgot_password()` - Password reset request
- `reset_password()` - Password recovery with token validation

### Subscription & Pricing (~250 lines)
- `premium_subscription()` - Comprehensive pricing page with:
  - Individual plans (Free, Standard, Professional, Researcher Plus)
  - Institutional plans (Lab License, Department, University Enterprise)
  - Japanese special offers (Pilot Program, MEXT Partnership)
  - Add-on services (custom prompts, on-premise, training, consultation, co-authorship)

### Donations & Support (~140 lines)
- `donate()` - Donation processing with payment methods:
  - Credit card integration
  - PayPal integration
  - GitHub Sponsors integration
  - Email verification and confirmation
  - Funding progress tracking
- `fundraising()` - Sustainability and fundraising information
- `donation_success()` - Success confirmation page

### Legal Pages (~20 lines)
- `privacy_policy()` - Privacy policy
- `terms_of_use()` - Terms of service
- `cookie_policy()` - Cookie consent policy
- `contact()` - Contact form and information

## REST API Endpoints

- `GET /api/subscription/` - User's subscription status
- `GET/POST /api/api-keys/` - List/create API keys
- `DELETE /api/api-keys/{id}/` - Revoke API key
- `GET /api/integrations/` - List connected services
- `POST /api/integrations/` - Add new integration
- `GET /api/resources/` - Usage metrics

## Database Operations

- Subscription plan creation and management
- User subscription lifecycle (creation, renewal, cancellation)
- API key generation and validation
- Service integration token storage
- Usage tracking and quota enforcement

## Authentication & Authorization

- **Public Views:** No authentication required
- **Authenticated Views:** User login required
- **Admin Operations:** Django admin access for staff
- **API Keys:** Alternative authentication for programmatic access

## Email Notifications

Triggered for:
- Account activation and welcome email
- Email verification codes via OTP
- Password reset instructions
- Donation confirmation and receipt
- Subscription renewal reminders
- Service integration confirmations

## Configuration

Located in `apps.py`:
- App name: `cloud_app`
- Default app configuration class

## Integration Points

- **auth_app:** User authentication and email verification
- **profile_app:** User profile information
- **donations_app:** Donation and funding models
- **Django Admin:** Subscription and APIKey management

## Monetization Features

1. **Subscription Model:** Tiered pricing with feature gates
2. **Donation System:** Multiple payment methods and transparency
3. **API Keys:** Programmatic access with rate limiting
4. **Usage Tracking:** CloudResource model for quota enforcement
5. **Service Integrations:** OAuth-based external service connections

## Testing

Test suite in `tests.py` covers:
- User signup and registration flows
- Login and authentication
- Email verification processes
- Donation submission and confirmation
- API key generation and validation
- Subscription plan management
- Service integration connectivity

## Future Improvements

1. **Extract Services:**
   - Move subscription logic to service layer
   - Move authentication logic to auth_app
   - Create dedicated payment_service for Stripe integration

2. **Modularize Views:**
   - Split 758-line views.py into multiple modules
   - Organize by feature (auth, subscription, donations, legal)

3. **Template Improvements:**
   - Separate concern-specific templates
   - Improve template inheritance structure

4. **Analytics:**
   - Track conversion metrics
   - Monitor subscription churn
   - Donation funnel analysis

## See Also

- `./apps/README.md` - App structure documentation
- `../auth_app/` - Authentication and user management
- `../accounts_app/` - User profiles, API keys, SSH keys, domain verification
- `../donations_app/` - Donation and funding models
- `../workspace_app/` - User projects and file management
