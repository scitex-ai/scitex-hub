# Password Reset Implementation

## Overview

Complete password reset functionality with email delivery, token validation, and secure password updates.

## Features

- ✅ Email-based password reset
- ✅ Secure token generation (Django's default_token_generator)
- ✅ 24-hour token expiration
- ✅ Real email delivery via scitex.ai mail server
- ✅ Password visibility toggle (eye button)
- ✅ Consistent UI with login page
- ✅ Security best practices (don't reveal if email exists)

## User Flow

```
1. User clicks "Forgot Password" on login page
   ↓
2. Enters email address
   ↓
3. Receives email from agent@scitex.ai
   ↓
4. Clicks reset link (valid 24 hours)
   ↓
5. Enters new password (with visibility toggle)
   ↓
6. Password reset successfully
   ↓
7. Redirected to login page
```

## Technical Implementation

### API Endpoints

**Forgot Password:**
```
POST /api/v1/auth/forgot-password/
Body: { "email": "user@example.com" }
Response: { "success": true, "message": "..." }
```

**Reset Password:**
```
POST /api/v1/auth/reset-password/
Body: {
  "uidb64": "...",
  "token": "...",
  "password": "newpassword"
}
Response: { "success": true, "message": "Password reset successfully" }
```

### Pages

**Forgot Password Page:**
- URL: `/forgot-password/`
- Template: `apps/cloud_app/templates/cloud_app/forgot_password.html`
- View: `apps/cloud_app/views.py::forgot_password()`

**Reset Password Page:**
- URL: `/reset-password/<uidb64>/<token>/`
- Template: `apps/cloud_app/templates/cloud_app/reset_password.html`
- View: `apps/cloud_app/views.py::reset_password()`

### Email Configuration

**Settings** (`config/settings/base.py`):
```python
SCITEX_CLOUD_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
SCITEX_CLOUD_EMAIL_HOST = 'smtp.gmail.com'  # Or mail1030.onamae.ne.jp
SCITEX_CLOUD_EMAIL_PORT = 587
SCITEX_CLOUD_EMAIL_USE_TLS = True
SCITEX_CLOUD_EMAIL_HOST_USER = os.environ.get('SCITEX_SENDER_GMAIL')
SCITEX_CLOUD_EMAIL_HOST_PASSWORD = os.environ.get('SCITEX_SENDER_GMAIL_PASSWORD')
```

**Environment Variables Required:**
```bash
SCITEX_SENDER_GMAIL=scitex.notification@gmail.com
SCITEX_SENDER_GMAIL_PASSWORD=app-password-here
```

### Security Features

1. **Token Expiration:** 24 hours
2. **One-time use:** Token invalidated after password change
3. **No email enumeration:** Always returns success (security best practice)
4. **Secure token generation:** Django's built-in PBKDF2 with salt
5. **HTTPS recommended:** For production deployment

## Testing

**Test Suite:** `/tests/test_forgot_password.py`

```bash
# Run all tests
python tests/test_forgot_password.py

# Run specific test
python tests/test_forgot_password.py --api-only
python tests/test_forgot_password.py --token-only

# Test with specific email
python tests/test_forgot_password.py --email admin@scitex.ai
```

**Test Coverage:**
- ✅ API endpoint functionality
- ✅ Token generation and validation
- ✅ Invalid email handling
- ✅ Missing email parameter
- ✅ Email delivery

## Troubleshooting

### Email Not Sending

1. Check environment variables are set:
   ```bash
   env | grep SCITEX.*EMAIL
   ```

2. Test email configuration:
   ```bash
   python tests/test_email.py
   ```

3. Check Django logs:
   ```bash
   tail -f logs/django.log | grep -i email
   ```

### Token Invalid/Expired

- Tokens expire after 24 hours
- Request new password reset if link expired
- Token is one-time use only

### Password Requirements

- Minimum 8 characters
- Enforced by HTML5 and Django validators
- Can be customized in `AUTH_PASSWORD_VALIDATORS` settings

## Files Modified

### Backend
- `apps/api/v1/auth/views.py` - Added `forgot_password()` and `reset_password()` API endpoints
- `apps/api/v1/auth/urls.py` - Added URL routes for both endpoints
- `apps/cloud_app/views.py` - Added `forgot_password()` and `reset_password()` page views
- `apps/cloud_app/urls.py` - Added URL routes for both pages

### Frontend
- `apps/cloud_app/templates/cloud_app/forgot_password.html` - Forgot password form
- `apps/cloud_app/templates/cloud_app/reset_password.html` - Reset password form with eye buttons

### Configuration
- `config/settings/base.py` - Email configuration with automatic SMTP detection
- `config/settings/development.py` - Development email settings

### Tests
- `tests/test_forgot_password.py` - Comprehensive test suite
- `tests/test_email.py` - Email configuration testing

## Production Deployment

### Email Provider Options

**Option 1: Gmail** (Current)
- Requires app password
- Free tier available
- Reliable delivery

**Option 2: scitex.ai Mail Server** (mail1030.onamae.ne.jp)
- Domain-based email (agent@scitex.ai)
- Professional appearance
- Full control

**Option 3: SendGrid/Mailgun** (Recommended for scale)
- Better deliverability
- Analytics and monitoring
- Higher sending limits

### Environment Variables for Production

```bash
# Gmail
export SCITEX_SENDER_GMAIL=scitex.notification@gmail.com
export SCITEX_SENDER_GMAIL_PASSWORD=your-app-password

# Or scitex.ai
export SCITEX_SCHOLAR_FROM_EMAIL_ADDRESS=agent@scitex.ai
export SCITEX_SCHOLAR_FROM_EMAIL_PASSWORD=your-password
export SCITEX_SCHOLAR_FROM_EMAIL_SMTP_SERVER=mail1030.onamae.ne.jp
export SCITEX_SCHOLAR_FROM_EMAIL_SMTP_PORT=587
```

## Future Enhancements

- [ ] Rate limiting on forgot password endpoint
- [ ] HTML email templates (currently plain text)
- [ ] Password strength meter on reset form
- [ ] Account lockout after multiple failed resets
- [ ] Email verification before password reset
- [ ] Multi-factor authentication option

---

**Status:** ✅ Fully implemented and tested
**Last Updated:** 2025-10-15
**Tested By:** test_forgot_password.py (4/4 tests passing)
