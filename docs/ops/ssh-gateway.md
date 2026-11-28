# SSH gateway

The Hub runs a public SSH login service, like the login node of an HPC
cluster. Users connect with their own SSH keys and get a shell in their
own workspace allocation. The shell comes from the same Terminal Broker path as the
web terminal: SLURM + Apptainer, with the environment the broker builds for
user processes.

| Entry point | Listener | Who |
|---|---|---|
| `ssh -p 2200 <user>@<host>` | `run_ssh_gateway` in the django container, port 2200 (`SCITEX_HUB_SSH_PORT_PROD`) | anyone with a registered key |
| `wss://<host>/ws/ssh/` | nginx → `ws_ssh_proxy` (websocat) → gateway | networks that block outbound SSH; needs a Hub session or API key **and** a registered key |

## Authentication

- Public keys only. Users manage their keys at **Settings → SSH keys**
  (`/accounts/settings/ssh-keys/`). Each key is stored as a `WorkspaceSSHKey`,
  and its "last used" time is shown there.
- Passwords and keyboard-interactive are refused. paramiko passes every such
  request to the server interface whatever `get_allowed_auths` advertises, so
  the refusal is explicit in `server_interface.py`.
- An unknown user and a wrong key get the same answer, so usernames cannot be enumerated.
- Interactive shells only. `exec`, `scp`/`sftp` subsystems and port forwarding
  are refused until they can be routed into the user's allocation.

WebSocket bridge client (the API key comes from Settings → API keys):

```
Host scitex
    HostName scitex.ai
    User <your-username>
    ProxyCommand websocat --binary -H "Authorization: Bearer ${SCITEX_API_KEY}" wss://scitex.ai/ws/ssh/
```

## Limits and temporary bans (in the gateway)

| Variable | Default | Meaning |
|---|---|---|
| `SCITEX_HUB_SSH_GATEWAY_MAX_CONCURRENT_PER_SOURCE` | 10 | open connections per source address |
| `SCITEX_HUB_SSH_GATEWAY_MAX_NEW_PER_MINUTE` | 30 | new connections per source address per minute |
| `SCITEX_HUB_SSH_GATEWAY_MAX_FAILURES` | 5 | failed connections before a ban |
| `SCITEX_HUB_SSH_GATEWAY_FAILURE_WINDOW_SECONDS` | 600 | window for counting failures |
| `SCITEX_HUB_SSH_GATEWAY_BAN_SECONDS` | 900 | ban length |
| `SCITEX_HUB_SSH_GATEWAY_MAX_AUTH_ATTEMPTS` | 12 | key checks per connection (one key = probe + signature = 2) |
| `SCITEX_HUB_SSH_GATEWAY_TRUSTED_PROXIES` | (empty) | comma-separated IPs, CIDRs or hostnames exempt from per-address limits; prod compose sets `ws_ssh_proxy` |

A *failed connection* is one that tried to authenticate and never succeeded.
The gateway counts connections rather than single attempts because an agent
offering several keys is normal. Both the source address and the attempted
username are counted and banned. Connections through the bridge are banned by
username only. State is in memory and resets when the gateway restarts.

Auth events go to the logger `scitex_hub.ssh_gateway.auth`, one line per event, in the
django container log:

```
ssh_auth event=key-rejected src=203.0.113.7 user=alice fingerprint=SHA256:...
ssh_auth event=ban src=203.0.113.7 user=alice key=ip:203.0.113.7
ssh_auth event=connection-refused src=203.0.113.7 reason=banned
ssh_auth event=login src=198.51.100.2 user=bob key=laptop
```

Events: `refused` (password, keyboard-interactive, banned user), `key-rejected`, `key-accepted`,
`too-many-attempts`, `login`, `logout`, `ban`, `connection-refused`,
`exec-refused`, `subsystem-refused`. Client-supplied fields are reduced to
`[A-Za-z0-9._@+-]`, so a log line cannot be forged.

## Host-level rate limit (operator step, optional but recommended)

The in-process limits run only after Python has accepted the TCP connection. For
scanning floods, also drop excess new connections in the kernel. On the
Docker host (published ports pass through the `DOCKER-USER` chain):

```
# iptables (Docker's own chains), port 2200 = the published gateway port
iptables -I DOCKER-USER -p tcp --dport 2200 -m conntrack --ctstate NEW \
  -m hashlimit --hashlimit-name ssh-gw --hashlimit-mode srcip \
  --hashlimit-above 20/minute --hashlimit-burst 20 -j DROP
```

Persist it with the host's firewall tooling, e.g. `netfilter-persistent save`.
fail2ban alternative: a filter matching `ssh_auth event=(key-rejected|refused) src=<HOST>`
on the django container log. The in-gateway ban already does the same.

## Moving to port 22

To serve on 22 like a login node, publish `22:2200` instead of `2200:2200`
(`SCITEX_HUB_SSH_PORT_PROD=22`). First move the host's own sshd off 22, or bind it
to the management network only. Remote host access currently goes through the
`bastion-nas` tunnel to `localhost:22`.

## Verification after a deploy

```
ssh -o PreferredAuthentications=password -p 2200 nobody@<host>   # must fail: "Permission denied (publickey)"
ssh -p 2200 <user>@<host>                                          # registered key: shell in the allocation
curl -s -o /dev/null -w '%{http_code}\n' -H 'Upgrade: websocket' -H 'Connection: Upgrade' \
  -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  https://<host>/ws/ssh/                                           # anonymous: 401
```
