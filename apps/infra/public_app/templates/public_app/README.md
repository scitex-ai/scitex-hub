# SciTeX Cloud App Templates

This directory contains the template files for the main cloud_app (landing pages, legal pages, etc.).

**Note:** Authentication templates have been moved to `apps/auth_app/templates/auth_app/` and monetization templates to `apps/donations_app/templates/donations_app/`.

## Directory Structure

```
cloud-app-templates/
├── landing_partials/        # Reusable components for landing page
├── pages/                   # General informational pages
├── products/                # Product-specific landing pages
├── base.html               # Base template for cloud_app
├── contact.html            # Contact form
├── cookie_policy.html      # Cookie policy page
├── features.html           # Features overview
├── landing.html            # Main landing page
├── privacy_policy.html     # Privacy policy
├── product_scholar.html    # Scholar product page
└── terms_of_use.html       # Terms of use
```

## Template Organization

### landing_partials/
Reusable components for building landing pages:
- Hero sections
- Feature cards
- Call-to-action blocks
- Testimonials

### pages/
General informational pages about the platform:
- About
- Concept
- Vision
- Roadmap
- Repositories

### products/
Individual product landing pages for SciTeX modules:
- Scholar
- Writer
- Code
- Viz
- Engine

## Moved Templates

### Authentication (→ apps/auth_app/templates/auth_app/)
- signin.html
- signup.html
- logout.html
- forgot_password.html
- reset_password.html
- email_verification.html
- verify_email.html

### Sustainability/Monetization (→ apps/donations_app/templates/donations_app/)
- pricing.html
- pricing_enhanced.html
- pricing_new.html
- premium_subscription.html
- donation_success.html

## Usage

These templates are used by `apps/cloud_app` and should extend from `base.html` or `templates/base.html` depending on the needs.

## Related Documentation

- Main templates directory: `/templates`
- Cloud app: `/apps/cloud_app`
- Auth app templates: `/apps/auth_app/templates/auth_app`
- Donations app templates: `/apps/donations_app/templates/donations_app`
- Design system: Available at `/dev/design.html`
