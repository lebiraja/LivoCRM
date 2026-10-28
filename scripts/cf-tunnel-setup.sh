#!/usr/bin/env bash
# One-time Cloudflare Tunnel setup from the server, no dashboard token copy needed.
# Usage: scripts/cf-tunnel-setup.sh livocrm.lebiraja.tech
# Prints a login link; open it, pick the domain, then this creates the tunnel,
# routes DNS, and writes TUNNEL_TOKEN to .env. The account cert is deleted at the end.
set -euo pipefail

HOST="${1:?usage: $0 <hostname>}"
NAME="livocrm"
IMAGE="cloudflare/cloudflared:2026.10.4"
CF_DIR="$(mktemp -d)"
trap 'rm -rf "$CF_DIR"' EXIT
cd "$(dirname "$0")/.."

cf() { docker run --rm -i --user "$(id -u):$(id -g)" -e HOME=/cf -v "$CF_DIR:/cf/.cloudflared" "$IMAGE" "$@"; }

cf tunnel login
cf tunnel list -o json | grep -q "\"name\":\"$NAME\"" || cf tunnel create "$NAME"
cf tunnel route dns --overwrite-dns "$NAME" "$HOST"
TOKEN="$(cf tunnel token "$NAME")"

touch .env && chmod 600 .env
sed -i '/^TUNNEL_TOKEN=/d' .env
printf 'TUNNEL_TOKEN=%s\n' "$TOKEN" >> .env
echo "Done: TUNNEL_TOKEN written to .env, $HOST -> tunnel $NAME."
echo "Route service in Cloudflare must be http://nginx:80 (set it under the tunnel's public hostnames if not shown)."
