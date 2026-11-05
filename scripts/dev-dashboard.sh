#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../apps/dashboard"
exec npm run dev
