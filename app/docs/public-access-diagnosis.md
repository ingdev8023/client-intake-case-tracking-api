# Public Access Diagnosis

This document tracks whether the self-hosted Client Intake & Case Tracking API server can be reached from the public internet.

Current local deployment stack:

```text
Nginx
  ↓
systemd-managed Gunicorn
  ↓
Flask API
  ↓
PostgreSQL
```

---

## 1. Current Status

* API works locally on the server: `Confirmed`
* API works through Gunicorn directly: `Confirmed`
* API works through Nginx locally: `Confirmed`
* API works through Nginx on LAN: `Confirmed`
* Public internet access: `Not available yet`
* Router access: `Login page available, credentials unavailable`
* Port forwarding control: `Not available`
* CGNAT status: `Unknown`
* HTTPS/domain configured: `No`

Current conclusion:

```text
The backend server is working correctly locally and on the LAN.
The API is not reachable from the public internet because the router/ISP edge cannot currently be configured.
```

---

## 2. Server LAN IP

Command:

```bash
hostname -I
```

Result:

```text
192.168.101.17 172.17.0.1
```

Selected server LAN IP:

```text
192.168.101.17
```

Notes:

```text
172.17.0.1 appears to be Docker/internal bridge network and should not be used for LAN testing.
```

---

## 3. Local Server Tests

### Test Nginx locally

Command:

```bash
curl -i http://127.0.0.1/health
```

Result:

```text
HTTP/1.1 200 OK
Server: nginx/1.28.3 (Ubuntu)
Content-Type: application/json

{"message":"API running"}
```

Conclusion:

```text
Nginx is running locally and correctly proxying requests to the Flask API.
```

---

### Test Gunicorn directly

Command:

```bash
curl -i http://127.0.0.1:8000/health
```

Result:

```text
HTTP/1.1 200 OK
Server: gunicorn
Content-Type: application/json

{"message":"API running"}
```

Conclusion:

```text
Gunicorn is serving the Flask API correctly on localhost port 8000.
```

---

### Test protected route through Nginx

Command:

```bash
curl http://127.0.0.1/cases
```

Expected result:

```json
{"msg":"Missing Authorization Header"}
```

Conclusion:

```text
Protected API routes are expected to reject unauthenticated requests.
```

---

## 4. LAN Test

Test device:

```text
Phone connected to the same WiFi/LAN
```

Test URL:

```text
http://192.168.101.17/health
```

Result:

```text
Success
```

Response:

```json
{"message":"API running"}
```

Conclusion:

```text
LAN access works. Another device on the local network can reach the API through Nginx.
```

Working LAN path:

```text
Phone on WiFi
  ↓
Router/LAN
  ↓
Server 192.168.101.17
  ↓
Nginx
  ↓
Gunicorn
  ↓
Flask API
```

---

## 5. Public IP Check

Command:

```bash
curl ifconfig.me
```

Result:

```text
181.78.78.115
```

Detected public IP:

```text
181.78.78.115
```

This is the IP used for the external mobile data test.

---

## 6. Router Access Status

Router gateway:

```text
192.168.101.1
```

Router management page:

```text
ONU Web Management System
```

Router login page:

```text
Available
```

Router admin credentials:

```text
Not available
```

Port forwarding access:

```text
Not available
```

WiFi/network configuration access:

```text
Not available
```

WAN IP visibility:

```text
Not available
```

Conclusion:

```text
The ISP-provided router/ONU is managed by the ISP. The user does not currently have credentials to configure WAN, NAT, port forwarding, WiFi settings, firewall rules, or inspect the router WAN IP.
```

---

## 7. CGNAT Diagnosis

Public IP from internet:

```text
181.78.78.115
```

Router WAN IP:

```text
Unknown
```

CGNAT status:

```text
Unknown
```

Reason:

```text
The router WAN IP cannot be inspected because router admin credentials are unavailable.
```

Important diagnostic rule:

```text
If router WAN IP matches 181.78.78.115, normal port forwarding may be possible.

If router WAN IP is in a private or carrier-grade range, such as 100.64.x.x, 10.x.x.x, 172.16.x.x - 172.31.x.x, or 192.168.x.x, the connection may be behind CGNAT or double NAT.
```

Current conclusion:

```text
CGNAT cannot be confirmed or ruled out yet.
```

---

## 8. Required Port Forwarding Rules

If router access becomes available, configure only these rules:

```text
External 80/tcp  → 192.168.101.17:80
External 443/tcp → 192.168.101.17:443
```

Do not forward:

```text
8000/tcp
5432/tcp
22/tcp
```

Reason:

```text
8000 is Gunicorn and should remain private behind Nginx.
5432 is PostgreSQL and should remain private.
22 is SSH and should not be exposed publicly unless intentionally hardened and approved.
```

The only public-facing service should be Nginx.

---

## 9. External Access Test

Test device:

```text
Phone using mobile data, WiFi disabled
```

Test URL:

```text
http://181.78.78.115/health
```

Result:

```text
Failed
```

Browser error:

```text
ERR_CONNECTION_REFUSED
```

Conclusion:

```text
The API is not currently reachable from the public internet.
```

Important interpretation:

```text
The local server and LAN access are working correctly. The failure is likely located at the router, ISP, port forwarding, firewall-at-router, CGNAT, or public network edge layer.
```

External path that currently fails:

```text
Phone on mobile data
  ↓
Internet
  ↓
Public IP 181.78.78.115
  ↓
ISP / Router / ONU edge
  ↓
Server 192.168.101.17
```

---

## 10. Findings

The API works locally and over the LAN.

Confirmed working layers:

```text
Flask API
Gunicorn
systemd service
Nginx reverse proxy
LAN access
```

Not confirmed or unavailable:

```text
Router WAN IP
Router admin access
Port forwarding
Public internet access
CGNAT status
```

Main finding:

```text
The issue is outside the Flask/Nginx/Gunicorn server stack and is located at the router/ISP network edge.
```

Current blocker:

```text
The ISP-provided router/ONU requires credentials that are not available to the user.
```

---

## 11. Possible Next Paths

### Option A: Contact ISP

Ask the ISP for router access, port forwarding, or confirmation of public IP/CGNAT status.

Suggested request in Spanish:

```text
Necesito habilitar port forwarding hacia un servidor local en mi red.

Necesito abrir los puertos 80 y 443 hacia la IP interna 192.168.101.17.

También necesito saber si mi servicio tiene una IP pública real o si está detrás de CGNAT.
```

Specific forwarding request:

```text
TCP 80  → 192.168.101.17:80
TCP 443 → 192.168.101.17:443
```

Do not ask to open:

```text
8000
5432
22
```

---

### Option B: Cloudflare Tunnel

Use Cloudflare Tunnel to expose the API without router port forwarding.

High-level architecture:

```text
Internet
  ↓
Cloudflare
  ↓
Cloudflare Tunnel running from the server
  ↓
Nginx / Flask API
```

Advantages:

```text
Works even when router access is limited
Often works behind CGNAT
Avoids manual port forwarding
Can integrate with domain and HTTPS
Good fit for a home-server learning project
```

Potential tradeoffs:

```text
Adds Cloudflare dependency
Requires Cloudflare account and tunnel configuration
Requires careful access/security configuration
```

---

### Option C: Tailscale

Use Tailscale for private access only.

High-level architecture:

```text
Laptop / Phone with Tailscale
  ↓
Private encrypted network
  ↓
Home server
```

Advantages:

```text
Very good for private admin/dev access
No public exposure required
Works behind locked routers and CGNAT
```

Tradeoff:

```text
Not ideal if the API needs to be publicly available to normal users without Tailscale.
```

---

### Option D: VPS Reverse Proxy

Use a small VPS as a public reverse proxy and keep the home server private.

High-level architecture:

```text
Internet
  ↓
VPS with public IP
  ↓
Tunnel or private connection
  ↓
Home server
```

Advantages:

```text
Professional infrastructure pattern
Good learning opportunity
Works around CGNAT/router restrictions
```

Tradeoffs:

```text
More complexity
Monthly VPS cost
Requires securing both VPS and home server
```

---

### Option E: Managed Hosting

Deploy the backend to a managed platform.

Possible platforms:

```text
Render
Railway
Fly.io
DigitalOcean App Platform
Other managed hosting providers
```

Advantages:

```text
Simpler public deployment
Less home-network complexity
Built-in public access path
```

Tradeoff:

```text
Less hands-on home server infrastructure learning.
```

---

## 12. Recommended Next Action

Recommended path:

```text
Evaluate Cloudflare Tunnel for public API access.
```

Reason:

```text
The API server is already working locally and on LAN.
The blocker is router/ISP access.
Cloudflare Tunnel can expose the service without requiring router port forwarding.
```

Next issue recommendation:

```text
Evaluate Cloudflare Tunnel for public API access
```

Suggested objective:

```text
Research and test whether Cloudflare Tunnel can expose the Flask API from the home server without requiring router port forwarding.
```

---

## 13. Current Decision

Normal router port forwarding path:

```text
Blocked for now
```

Reason:

```text
Router credentials are unavailable.
```

Public access path selected for future evaluation:

```text
Cloudflare Tunnel
```

---

## 14. Security Notes

Do not expose Gunicorn directly.

Gunicorn must remain bound to:

```text
127.0.0.1:8000
```

Do not expose PostgreSQL.

PostgreSQL must remain local/private.

Do not forward:

```text
8000
5432
22
```

Only Nginx should be public-facing:

```text
80
443
```

Before any public exposure, confirm:

* UFW is active
* Nginx is the only public-facing service
* Gunicorn is private
* PostgreSQL is private
* JWT secret is strong
* CORS origins are restricted
* `.env` is not committed
* `.env` permissions are restricted
* backups are planned
* logs are reviewed

---

## 15. Final Summary

The public access diagnosis was successful.

It confirmed that the backend server is healthy and reachable inside the LAN, but not publicly reachable from the internet.

The blocker is not the application stack.

The blocker is the ISP/router edge:

```text
No router admin credentials
No port forwarding access
Unknown CGNAT status
```

Recommended next step:

```text
Evaluate Cloudflare Tunnel as the public access strategy.
```
