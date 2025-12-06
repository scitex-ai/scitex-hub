# SciTeX Integrations - Activation Checklist

## ✅ Already Completed

Your SciTeX system already has automatic discovery enabled:

1. **App Discovery** ✅
   - `config/settings/settings_shared.py:45` has `discover_local_apps()`
   - `integrations_app` is automatically detected and added to `INSTALLED_APPS`
   - No manual configuration needed!

2. **URL Discovery** ✅
   - `config/urls.py:273` has `discover_app_urls()`
   - `integrations_app/urls.py` is automatically registered at `/integrations/`
   - No manual URL configuration needed!

3. **Settings Configuration** ✅
   - ORCID OAuth settings added to `config/settings/settings_shared.py:324`
   - Uses environment variables for credentials
   - Defaults are safe for development

## 🚀 Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
pip install requests cryptography
```

Or if you have a requirements file:

```bash
# Add to requirements.txt:
requests>=2.31.0
cryptography>=41.0.0
```

### Step 2: Run Migrations

```bash
python manage.py makemigrations integrations_app
python manage.py migrate
```

### Step 3: Set Environment Variables (Optional)

For ORCID integration, create a `.env` file or export:

```bash
# Development (using ORCID sandbox)
export ORCID_CLIENT_ID="APP-XXXXXXXXXXXXX"
export ORCID_CLIENT_SECRET="your-secret-here"
export ORCID_REDIRECT_URI="http://localhost:8000/integrations/orcid/callback/"

# Production
export ORCID_CLIENT_ID="APP-XXXXXXXXXXXXX"
export ORCID_CLIENT_SECRET="your-production-secret"
export ORCID_REDIRECT_URI="https://yourdomain.com/integrations/orcid/callback/"
```

To get ORCID credentials:
- Sandbox (dev): https://sandbox.orcid.org/developer-tools
- Production: https://orcid.org/developer-tools

### Step 4: Access Integrations

```bash
python manage.py runserver
```

Then visit:
- Dashboard: http://localhost:8000/integrations/
- Admin: http://localhost:8000/admin/integrations_app/

## 🎯 What Works Right Now

### Without Configuration:
- ✅ Integration dashboard page loads
- ✅ Slack webhook configuration
- ✅ BibTeX export (from any project)
- ✅ Admin interface

### With ORCID Credentials:
- ✅ ORCID OAuth login
- ✅ Profile syncing
- ✅ Author data auto-population

## 📋 Integration URLs

All automatically available at:

```
/integrations/                          # Dashboard
/integrations/orcid/connect/           # ORCID OAuth start
/integrations/orcid/callback/          # ORCID OAuth callback
/integrations/orcid/sync/              # Manual profile sync
/integrations/orcid/disconnect/        # Disconnect ORCID
/integrations/slack/configure/         # Slack setup form
/integrations/export/<project_id>/bib/ # Download .bib file
/integrations/api/status/              # API: integration status
/integrations/api/orcid/profile/       # API: ORCID profile data
```

## 🔧 Optional: Add to Navigation

To add integrations to your main navigation, edit your base template:

```django
<!-- In templates/workspace_app/base.html or similar -->
<nav>
  ...
  <a href="{% url 'integrations_app:dashboard' %}">Integrations</a>
  ...
</nav>
```

## 🧪 Testing

### Test Without ORCID (works immediately):

1. Visit dashboard:
   ```
   http://localhost:8000/integrations/
   ```

2. Configure Slack webhook:
   - Get webhook URL from Slack: https://api.slack.com/messaging/webhooks
   - Paste into form at `/integrations/slack/configure/`
   - Test notification

3. Export bibliography:
   - Go to any project page
   - Add link: `{% url 'integrations_app:export_project_bib' project.id %}`
   - Click to download .bib file

### Test With ORCID (requires credentials):

1. Set ORCID environment variables (see Step 3)

2. Click "Connect ORCID" on dashboard

3. Authorize on ORCID (sandbox or production)

4. View synced profile data

## 🔐 Security Notes

- **Tokens are encrypted** using Django's SCITEX_CLOUD_DJANGO_SECRET_KEY before storage
- **Use HTTPS in production** for all OAuth redirects
- **Never commit** ORCID credentials to git
- **Use environment variables** for all sensitive data

## 📝 Usage Examples

### In Your Views:

```python
# Send Slack notification
from apps.integrations_app.services.slack_service import notify_project_created

notify_project_created(project)

# Export bibliography
from apps.integrations_app.services import BibExportService

service = BibExportService(project)
bibtex = service.generate_bibtex(references)

# Get ORCID profile
if request.user.integration_connections.filter(service='orcid', status='active').exists():
    connection = request.user.integration_connections.get(service='orcid')
    profile = connection.orcid_profile
    author_name = profile.get_full_name()
```

### In Templates:

```django
<!-- Export bibliography button -->
<a href="{% url 'integrations_app:export_project_bib' project.id %}"
   class="btn btn-primary">
    Export Bibliography (.bib)
</a>

<!-- Show ORCID status -->
{% if user.integration_connections.filter(service='orcid', status='active').exists %}
    <span class="badge badge-success">ORCID Connected</span>
{% else %}
    <a href="{% url 'integrations_app:orcid_connect' %}">Connect ORCID</a>
{% endif %}
```

## 📚 Documentation

Complete documentation available at:
- **Setup Guide**: `docs/INTEGRATIONS_SETUP.md`
- **Implementation Summary**: `docs/INTEGRATIONS_IMPLEMENTATION_SUMMARY.md`
- **Roadmap**: `TODOS/INTEGRATIONS.md`

## ⚡ That's It!

The integrations are **ready to use** with just:
1. `pip install requests cryptography`
2. `python manage.py migrate`
3. Optional: Set ORCID credentials for OAuth

Everything else (app registration, URL routing, settings) is **already done automatically** through the discovery system!

---

Need help? Check the troubleshooting section in `docs/INTEGRATIONS_SETUP.md`
