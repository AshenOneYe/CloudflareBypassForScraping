#!/usr/bin/env python3
"""Bake the GeoLite2-City database into the image at build time.

`cf_bypasser.core.bypasser.setup_browser` enables `geoip=True` whenever a proxy
is configured, and cloakbrowser then resolves the proxy's timezone/locale from
GeoLite2-City.mmdb. That database is downloaded (~70 MB) from GitHub on first
use, inside the container, over a direct connection.

Doing it here instead means the published image already contains the database,
so containers that can only reach the internet through a proxy (or not at all
until a proxy is up) still work. Without the database every proxied launch fails
with "GeoIP resolution failed: GeoIP database is unavailable", and without the
`geoip2` package (cloakbrowser[geoip]) it fails even earlier with an ImportError.
"""

import sys
import time
from pathlib import Path

ATTEMPTS = 3

try:
    from cloakbrowser.geoip import GEOIP_DB_FILENAME, GEOIP_DB_URL, _get_geoip_dir
except ImportError as exc:  # pragma: no cover - only on a broken install
    print(f"cannot import cloakbrowser.geoip: {exc}", file=sys.stderr)
    sys.exit(1)


def db_path() -> Path:
    return _get_geoip_dir() / GEOIP_DB_FILENAME


def _download_direct() -> bool:
    """Fallback for cloakbrowser versions without a public ensure helper."""
    import httpx

    dest = db_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {GEOIP_DB_URL} -> {dest}")
    with httpx.stream("GET", GEOIP_DB_URL, follow_redirects=True, timeout=300.0) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_bytes(chunk_size=65_536):
                fh.write(chunk)
    return dest.exists()


def fetch() -> bool:
    if db_path().exists():
        return True
    try:
        from cloakbrowser.geoip import _ensure_geoip_db
    except ImportError:
        return _download_direct()
    return bool(_ensure_geoip_db()) and db_path().exists()


def main() -> int:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            if fetch() and db_path().exists():
                size_mb = db_path().stat().st_size / 1e6
                print(f"GeoIP database ready: {db_path()} ({size_mb:.1f} MB)")
                return 0
        except Exception as exc:
            print(f"attempt {attempt}/{ATTEMPTS} failed: {exc}", file=sys.stderr)
        time.sleep(2 * attempt)

    print(
        "GeoIP database unavailable -- every proxied launch would fail with "
        "'GeoIP resolution failed: GeoIP database is unavailable'",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
