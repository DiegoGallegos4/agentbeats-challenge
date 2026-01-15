#!/usr/bin/env bash
set -euo pipefail

GREEN_HOST="127.0.0.1"
GREEN_PORT="9009"
PURPLE_HOST="127.0.0.1"
PURPLE_PORT="9010"

python src/green/server.py --host "${GREEN_HOST}" --port "${GREEN_PORT}" &
GREEN_PID=$!
python src/purple/server.py --host "${PURPLE_HOST}" --port "${PURPLE_PORT}" &
PURPLE_PID=$!

cleanup() {
  kill "${GREEN_PID}" "${PURPLE_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

python - <<'PY'
import socket
import time

hosts = [("127.0.0.1", 9009), ("127.0.0.1", 9010)]

def wait_for(host, port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False

for host, port in hosts:
    ok = wait_for(host, port)
    status = "ok" if ok else "failed"
    print(f"port {port}: {status}")
    if not ok:
        raise SystemExit(1)
PY

echo "Both agents are listening."
