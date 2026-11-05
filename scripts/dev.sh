#!/usr/bin/env sh
set -eu

api_pid=
dashboard_pid=

cleanup() {
  [ -z "$api_pid" ] || kill "$api_pid" 2>/dev/null || true
  [ -z "$dashboard_pid" ] || kill "$dashboard_pid" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

academix serve &
api_pid=$!

(cd "$(dirname "$0")/../apps/dashboard" && npm run dev) &
dashboard_pid=$!

wait "$api_pid" "$dashboard_pid"
