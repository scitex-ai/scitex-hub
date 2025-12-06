# Email Sender Avatar/Icon Setup Guide

This guide explains how to display the SciTeX logo as the sender avatar in email clients (Gmail, Yahoo, etc.)

## Current Status
- ✅ Favicon configured for website
- ✅ Logo embedded in email body
- ❌ DMARC not configured
- ❌ BIMI not configured
- ❌ Sender avatar not showing

## Option 1: BIMI (Brand Indicators for Message Identification) - RECOMMENDED

BIMI is the official standard supported by Gmail, Yahoo, Fastmail, and other major email providers.

### Prerequisites

1. **DMARC Policy** (Required)
   - Must have DMARC policy set to `quarantine` or `reject`
   - Add this DNS TXT record for `_dmarc.scitex.ai`:
   ```
   v=DMARC1; p=quarantine; rua=mailto:dmarc@scitex.ai; pct=100; adkim=s; aspf=s
   ```

2. **SPF Record** (Should already exist)
   - Verify SPF is configured for mail1030.onamae.ne.jp
   - Check existing record: `dig TXT scitex.ai`

3. **DKIM** (Should already exist)
   - Verify DKIM is configured by your email provider (Onamae)

### Step 1: Create SVG Logo

The logo must be:
- **Format:** SVG Tiny Portable/Secure (SVG-PS)
- **Size:** Square aspect ratio (recommended 512x512 or 1024x1024)
- **Colors:** Can be full color
- **Location:** Hosted on HTTPS

**Convert your PNG logo to SVG:**

```bash
# Option 1: Use online converter
# Upload: /static/images/logo_files/png/Color logo - S.png
# To: https://convertio.co/png-svg/

# Option 2: Use ImageMagick (if available)
convert "/home/ywatanabe/proj/scitex-cloud/static/images/logo_files/png/Color logo - S.png" \
  -background none \
  "/home/ywatanabe/proj/scitex-cloud/static/images/logo_files/svg/scitex-bimi-logo.svg"
```

**Save the SVG at:**
```
/home/ywatanabe/proj/scitex-cloud/static/images/logo_files/svg/scitex-bimi-logo.svg
```

### Step 2: Host the SVG Logo

Make the logo accessible at:
```
https://scitex.ai/static/images/logo_files/svg/scitex-bimi-logo.svg
```

**Verify it's accessible:**
```bash
curl -I https://scitex.ai/static/images/logo_files/svg/scitex-bimi-logo.svg
```

### Step 3: Add BIMI DNS Record

Add a TXT record for `default._bimi.scitex.ai`:

```
v=BIMI1; l=https://scitex.ai/static/images/logo_files/svg/scitex-bimi-logo.svg;
```

**Complete DNS setup:**
1. Log into your DNS provider (Onamae.ne.jp)
2. Add TXT record:
   - **Name:** `default._bimi`
   - **Type:** TXT
   - **Value:** `v=BIMI1; l=https://scitex.ai/static/images/logo_files/svg/scitex-bimi-logo.svg;`
   - **TTL:** 3600

### Step 4: Verify BIMI Setup

**Check DNS propagation:**
```bash
dig TXT default._bimi.scitex.ai
```

**Test with BIMI Inspector:**
- https://bimigroup.org/bimi-generator/
- Enter domain: scitex.ai
- Check if logo displays correctly

### Step 5: Wait for Email Clients to Adopt

- **Gmail:** Usually takes 1-7 days after proper BIMI setup
- **Yahoo:** Usually immediate after verification
- **Without VMC:** Logo shows but no verified checkmark
- **With VMC:** Logo shows with blue verified checkmark (costs ~$1500/year)

---

## Option 2: Gravatar (Free, Quick, Limited)

Gmail sometimes shows Gravatar images for senders.

### Steps:
1. Go to https://gravatar.com
2. Register with `agent@scitex.ai`
3. Upload SciTeX logo
4. Make profile public

**Limitations:**
- Only works on some email clients
- Less reliable than BIMI
- Requires email verification

---

## Option 3: Google Postmaster Tools (Gmail Only)

For Gmail users to see your logo:

1. Visit https://postmaster.google.com
2. Add and verify domain: scitex.ai
3. Upload logo (square, at least 512x512px)

**Limitations:**
- Gmail only
- Requires domain verification
- Not as widely adopted as BIMI

---

## Recommended Implementation Order

1. ✅ **Week 1:** Set up DMARC policy
   - Start with `p=none` for monitoring
   - Review reports for 2 weeks
   - Then change to `p=quarantine`

2. ✅ **Week 3:** Create and host SVG logo
   - Convert PNG to SVG
   - Validate SVG format
   - Upload to static files

3. ✅ **Week 3:** Add BIMI DNS record
   - Add TXT record
   - Verify DNS propagation
   - Test with BIMI inspector

4. ⏱ **Week 4-5:** Wait for adoption
   - Email clients cache DNS
   - Send test emails
   - Monitor inbox appearance

5. 🔄 **Future:** Consider VMC for verified checkmark
   - Only if budget allows (~$1500/year)
   - Adds blue checkmark in Gmail
   - Increases trust/credibility

---

## Testing Your Setup

**Send test emails:**
```bash
./tests/test_email.py your-gmail-address@gmail.com
```

**Check in different clients:**
- Gmail (web)
- Gmail (mobile app)
- Yahoo Mail
- Outlook.com
- Apple Mail

---

## Troubleshooting

### Logo not showing after 7 days?

1. **Verify DMARC is active:**
   ```bash
   dig TXT _dmarc.scitex.ai
   ```

2. **Verify BIMI record:**
   ```bash
   dig TXT default._bimi.scitex.ai
   ```

3. **Check SVG is accessible:**
   ```bash
   curl https://scitex.ai/static/images/logo_files/svg/scitex-bimi-logo.svg
   ```

4. **Validate SVG format:**
   - Use: https://bimi-svg-converter.com/
   - SVG must be Tiny Portable/Secure spec

5. **Check DMARC compliance:**
   - Must pass both SPF and DKIM
   - Policy must be quarantine or reject
   - Alignment must be strict

---

## Current Email Configuration

```
SCITEX_CLOUD_EMAIL_HOST: mail1030.onamae.ne.jp
SCITEX_CLOUD_EMAIL_PORT: 587
SCITEX_CLOUD_EMAIL_USE_TLS: True
SCITEX_CLOUD_EMAIL_HOST_USER: agent@scitex.ai
DEFAULT_FROM_EMAIL: agent@scitex.ai
```

---

## Additional Resources

- BIMI Group: https://bimigroup.org/
- BIMI Generator: https://bimigroup.org/bimi-generator/
- DMARC Guide: https://dmarc.org/
- Google Postmaster: https://postmaster.google.com/
- BIMI Inspector: https://www.mailhardener.com/tools/bimi-inspector

---

## Estimated Timeline

- **Immediate:** Logo in email body ✅ (already done)
- **1-2 days:** DNS setup (DMARC + BIMI)
- **3-7 days:** Gmail starts showing logo
- **1-2 weeks:** Most email clients showing logo

---

## Cost Breakdown

- **BIMI without VMC:** FREE (logo shows, no checkmark)
- **BIMI with VMC:** ~$1500/year (logo + verified checkmark)
- **Domain/DNS:** Already covered
- **Logo design:** Already have it

**Recommendation:** Start with free BIMI (no VMC) and upgrade to VMC if needed for credibility.
