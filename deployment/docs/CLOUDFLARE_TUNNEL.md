<!-- ---
!-- Timestamp: 2025-11-25 10:01:48
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/CLOUDFLARE_TUNNEL.md
!-- --- -->

# Self-Hosting with Cloudflare Tunnel

## Prerequisites

- A home server (NAS, etc.) with Docker running
- A domain name (e.g., scitex.ai)
- A Cloudflare account

## 1. Create a Cloudflare Tunnel

1. Log in to https://one.dash.cloudflare.com/
2. Navigate to Networks → Connectors → Create a tunnel
3. Select Cloudflared
4. Enter a tunnel name (e.g., my_nas)
5. Copy the token that is displayed

## 2. Server-Side Configuration

### Add token to environment variables
```bash
# Add to .env file
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoixxxxxxx...
```

### Add cloudflared to docker-compose.yml
```yaml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
    restart: always
    networks:
      - your-network
    depends_on:
      - nginx  # or your web service
```

### Start the service
```bash
docker compose up -d
```

### Verify connection
```bash
docker compose logs cloudflared
# Success if you see "Registered tunnel connection"
```

## 3. Add Domain to Cloudflare

1. Go to https://dash.cloudflare.com/ and click + Add → Add a domain
2. Enter your domain name (e.g., scitex.ai)
3. Select the Free plan
4. Note the nameservers Cloudflare assigns:
   - e.g., milan.ns.cloudflare.com
   - e.g., monika.ns.cloudflare.com

## 4. Update Nameservers at Your Domain Registrar

At your registrar (e.g., GoDaddy, Namecheap, お名前.com):

1. Go to domain settings → Nameserver configuration
2. Select your domain
3. Choose "Use custom nameservers"
4. Enter the Cloudflare nameservers
5. Save and confirm

Propagation takes 15 minutes to 24 hours.

### Verify DNS Propagation

Use https://www.whatsmydns.net/ to check propagation status worldwide:

1. Enter your domain (e.g., scitex.ai)
2. Select record type from dropdown:
   - **NS** - Check nameserver propagation first
   - **A** - Check IP address propagation after Public Hostname is configured
3. Click Search

**NS record check:**
- ✅ Complete when all regions show Cloudflare nameservers (e.g., `milan.ns.cloudflare.com`)
- ❌ Still propagating if regions show old nameservers (e.g., `ns-rs1.gmoserver.jp`)

**A record check (after step 5):**
- ✅ Complete when all regions show Cloudflare IPs
- ❌ Still propagating if regions show your old server IP

You can also verify via command line:
```bash
# Check nameservers
dig yourdomain.com NS +short

# Check A record
dig yourdomain.com A +short
```

## 5. Configure Public Hostname

After nameservers have propagated (NS check shows Cloudflare nameservers):

1. Go to https://one.dash.cloudflare.com/
2. Navigate to Networks → Connectors → Click your tunnel name
3. Go to Published application routes tab
4. Click Add a route and enter:

| Field     | Value                         |
|-----------|-------------------------------|
| Subdomain | (leave empty for root domain) |
| Domain    | yourdomain.com                |
| Type      | HTTP                          |
| URL       | nginx:80                      |

Add subdomains similarly:

| Field     | Value          |
|-----------|----------------|
| Subdomain | git            |
| Domain    | yourdomain.com |
| Type      | HTTP           |
| URL       | gitea:3000     |

## 6. Verify Deployment

1. Check A record propagation at https://www.whatsmydns.net/ (select **A** from dropdown)
2. Access https://yourdomain.com in your browser
3. SSL is handled automatically by Cloudflare - no certificate configuration needed

## Benefits

- No VPS required, zero monthly cost
- No static IP address needed
- No port forwarding required
- Automatic SSL
- DDoS protection included

## Troubleshooting

### "Invalid nameservers" in Cloudflare dashboard
- Nameserver change not yet propagated
- Verify at https://www.whatsmydns.net/ with NS record type
- Wait 15 minutes to 24 hours

### Tunnel shows "INACTIVE" or "UNHEALTHY"
```bash
docker compose logs cloudflared
```
- Check if token is correct in .env file
- Ensure cloudflared container is running

### Site not accessible after Public Hostname setup
- Check A record propagation at whatsmydns.net
- Verify internal service is running: `docker compose ps`
- Check nginx/web service logs: `docker compose logs nginx`

<!-- EOF -->