"""Guarantee a usable X display for the headed stealth browser.

Chromium is launched headed on purpose (managed Turnstile does not clear in
headless mode), so a missing X server turns every request into Playwright's
"Missing X server or $DISPLAY" and a failed bypass.

`docker-entrypoint.sh` normally starts Xvfb for us, but that only helps when the
entrypoint actually runs: overriding `command:`/`entrypoint:` in compose, or an
Xvfb that dies on startup, leaves the server without a display. This module
starts Xvfb on demand so the server works however the container is launched.
"""

import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

_log = logging.getLogger(__name__)

# Escape hatch for hosts that provide their own X server or want the raw error.
AUTO_XVFB = os.environ.get("CF_AUTO_XVFB", "1").lower() not in ("0", "false", "no", "off")
DISPLAY_NUM = os.environ.get("DISPLAY_NUM", "99")
START_TIMEOUT_SECONDS = 10.0

_lock = threading.Lock()
_proc: "subprocess.Popen | None" = None


def _socket_path(display: str) -> Path:
    return Path("/tmp/.X11-unix/X%s" % display.lstrip(":"))


def _usable(display: str) -> bool:
    """An X display is only usable if $DISPLAY is set and its socket exists."""
    return bool(display) and _socket_path(display).exists()


def _spawn_xvfb(display: str) -> bool:
    global _proc

    if not shutil.which("Xvfb"):
        _log.error(
            "no usable X server (%s) and Xvfb is not installed; "
            "the headed browser launch will fail", os.environ.get("DISPLAY") or "$DISPLAY unset"
        )
        return False

    try:
        Path("/tmp/.X11-unix").mkdir(parents=True, exist_ok=True)
    except OSError as e:  # pragma: no cover - only on exotic mounts
        _log.warning("could not create /tmp/.X11-unix: %s", e)

    _log.warning(
        "no X server on %s -- starting Xvfb in-process (docker-entrypoint.sh normally "
        "does this; a compose command/entrypoint override skips it)", display
    )
    _proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", "1920x1080x24", "-nolisten", "tcp", "-ac"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    deadline = time.monotonic() + START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _socket_path(display).exists():
            return True
        if _proc.poll() is not None:
            _log.error("Xvfb exited immediately (code %s)", _proc.returncode)
            _proc = None
            return False
        time.sleep(0.1)

    _log.error("Xvfb did not create %s within %.0fs", _socket_path(display), START_TIMEOUT_SECONDS)
    return False


def ensure_display() -> bool:
    """Ensure $DISPLAY points at a live X server, starting Xvfb if needed.

    Cheap and idempotent: when the entrypoint already provided a display this is
    a single stat() call. Returns True when a display is ready.
    """
    if _usable(os.environ.get("DISPLAY", "")):
        return True
    if not AUTO_XVFB:
        return False

    with _lock:
        if _usable(os.environ.get("DISPLAY", "")):
            return True

        display = ":%s" % DISPLAY_NUM
        if not _socket_path(display).exists() and not _spawn_xvfb(display):
            return False

        os.environ["DISPLAY"] = display
        _log.info("X display ready on %s", display)
        return True
