#!/usr/bin/env bash
# Deploy one commit on the Cloudflare-Tunnel server (builds images on the host).
# Run by GitHub Actions over SSH (from a /tmp copy, so checkouts cannot rewrite it mid-run), or by hand.
# Usage: scripts/deploy-server.sh [sha]  (default: origin/main). APP_DIR defaults to ~/LivoCRM.
# On failure it rolls back to the previously deployed commit.
set -euo pipefail

main() {
  cd "${APP_DIR:-$HOME/LivoCRM}"
  local compose=(docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml)
  local prev target
  prev="$(git rev-parse HEAD)"
  git fetch --quiet origin main
  target="${1:-$(git rev-parse origin/main)}"
  [[ "$target" =~ ^[0-9a-f]{40}$ ]] || { echo "deploy: need a full commit sha" >&2; return 2; }

  git checkout --quiet main
  git merge --quiet --ff-only "$target"

  release() {
    "${compose[@]}" pull --quiet db redis nginx cloudflared
    "${compose[@]}" build --pull backend frontend
    "${compose[@]}" up -d --wait --remove-orphans
  }

  if release; then
    docker image prune -f --filter "until=168h" >/dev/null
    echo "deployed $(git rev-parse --short HEAD)"
    return 0
  fi

  echo "deploy failed, rolling back to ${prev:0:7}" >&2
  "${compose[@]}" logs --tail=40 backend nginx cloudflared >&2 || true
  git reset --quiet --hard "$prev"
  release || echo "rollback also failed, check the host" >&2
  return 1
}

main "$@"
exit $?
