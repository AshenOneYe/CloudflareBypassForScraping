# Configuration

All runtime configuration is via environment variables. Every variable is optional and falls back to the default shown below. Set them before starting `server.py` (or in your Docker/compose `environment:` block).

## Cookie cache

| Variable | Default | Description |
|---|---|---|
| `CF_COOKIE_TTL_MINUTES` | `29` | How long generated Cloudflare clearance cookies are cached before they're considered expired and regenerated. Cloudflare `cf_clearance` cookies are short-lived, so keep this under ~30 minutes. |

## Proxy exit-IP check

A rotating residential proxy can change its exit IP unexpectedly, which invalidates the `cf_clearance` cookie bound to the old IP. When enabled, the bypasser checks the proxy's current exit IP on each cache hit and, if it changed since the cookies were generated, invalidates the cache immediately and regenerates. Disabled by default (adds one HTTP request per cache hit when on).

| Variable | Default | Description |
|---|---|---|
| `CF_IP_CHECK_ENABLED` | `false` | Enable the exit-IP check. Accepts `1`/`true`/`yes`/`on`. |
| `CF_IP_CHECK_URL` | `https://api.ipify.org` | Endpoint that echoes the caller's IP as plain text. The request is made through the active proxy. |
| `CF_IP_CHECK_TIMEOUT` | `10` | Timeout in seconds for the exit-IP request. |

## Concurrency & resources

| Variable | Default | Description |
|---|---|---|
| `CF_MAX_CONCURRENT_BROWSERS` | `4` | Maximum number of stealth-browser contexts launched at the same time. Caps memory/CPU under load; extra requests queue. |
| `CF_MAX_SESSIONS` | `128` | Maximum number of cached `curl_cffi` mirror sessions (LRU, one per `hostname:proxy`). The least-recently-used session is closed and evicted past this limit. |

## Browser engine (CloakBrowser)

Requests that carry a proxy are launched with `geoip=True`, so CloakBrowser derives the browser timezone/locale from the proxy's exit IP. That needs the `geoip` extra (`geoip2` + `socksio`, installed via `cloakbrowser[geoip]` in `server_requirements.txt`) **and** the ~70 MB `GeoLite2-City.mmdb`, which is downloaded on first use into `~/.cloakbrowser/geoip/`. The Docker image bakes the database in at build time (`scripts/fetch_geoip_db.py`) so containers whose only route out is a proxy never have to fetch it from GitHub at runtime. Missing either one makes every proxied launch fail (`geoip2 is required for geoip=True`, or `GeoIP resolution failed: GeoIP database is unavailable`).

| Variable | Default | Description |
|---|---|---|
| `CLOAKBROWSER_AUTO_UPDATE` | `false` | Set to `false` by the app so it does not check PyPI for a newer Chromium build on every launch. The bundled CloakBrowser library also reads `CLOAKBROWSER_BINARY_PATH`, `CLOAKBROWSER_CACHE_DIR`, and `CLOAKBROWSER_DOWNLOAD_URL` — see the CloakBrowser docs. |
| `CLOAKBROWSER_CACHE_DIR` | `~/.cloakbrowser` | Where CloakBrowser keeps the Chromium build and the GeoIP database. Point it at a mounted volume to persist them across container recreations. |

## Virtual display (containers)

The stealth browser is always launched **headed** (managed Turnstile does not clear headless), so a Linux container needs an X server. `docker-entrypoint.sh` starts `Xvfb` on `:99` for you; if the display is missing at launch time (for example when compose overrides `command:`/`entrypoint:`, which skips the entrypoint), the app starts `Xvfb` itself as a fallback. Without a display every request fails with `Missing X server or $DISPLAY`.

| Variable | Default | Description |
|---|---|---|
| `DISPLAY_NUM` | `99` | X display number used by the entrypoint and by the in-app fallback. |
| `CF_AUTO_XVFB` | `true` | Let the app start `Xvfb` when no usable display exists. Set to `false` if the host provides its own X server and you want the raw error instead. |

## Example

```bash
export CF_COOKIE_TTL_MINUTES=20
export CF_IP_CHECK_ENABLED=true
export CF_MAX_CONCURRENT_BROWSERS=8
python server.py
```
