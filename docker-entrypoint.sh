#!/bin/sh
set -eu

# Headed Chromium needs a display, and managed Turnstile needs a headed browser,
# so a missing X server means every request fails with
# "Missing X server or $DISPLAY". Start Xvfb ourselves instead of via xvfb-run,
# whose readiness handshake hangs in containers (never exec'ing the server).
DISPLAY_NUM="${DISPLAY_NUM:-99}"

if [ -n "${DISPLAY:-}" ] && [ -S "/tmp/.X11-unix/X${DISPLAY#:}" ]; then
    echo "docker-entrypoint: reusing display ${DISPLAY}"
else
    mkdir -p /tmp/.X11-unix
    Xvfb ":${DISPLAY_NUM}" -screen 0 1920x1080x24 -nolisten tcp -ac >/tmp/xvfb.log 2>&1 &
    XVFB_PID=$!
    export DISPLAY=":${DISPLAY_NUM}"

    # wait for the X socket so the first browser launch has a ready display
    waited=0
    while [ "$waited" -lt 100 ]; do
        [ -S "/tmp/.X11-unix/X${DISPLAY_NUM}" ] && break
        if ! kill -0 "$XVFB_PID" 2>/dev/null; then
            echo "docker-entrypoint: Xvfb died during startup:" >&2
            cat /tmp/xvfb.log >&2 || true
            break
        fi
        waited=$((waited + 1))
        sleep 0.1
    done

    if [ -S "/tmp/.X11-unix/X${DISPLAY_NUM}" ]; then
        echo "docker-entrypoint: Xvfb ready on ${DISPLAY} (pid ${XVFB_PID})"
    else
        # don't abort: the app retries via cf_bypasser.utils.display and logs why
        echo "docker-entrypoint: Xvfb NOT ready on ${DISPLAY} after 10s" >&2
        cat /tmp/xvfb.log >&2 || true
    fi
fi

exec python3 server.py "$@"
