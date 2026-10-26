#!/usr/bin/env bash
# Deploy one commit on the app host. Run by SSM Run Command from the GitHub Actions deploy job,
# and by hand for rollbacks (see cloud/deploy/README.md).
# Usage: deploy.sh <40-char-commit-sha> <ecr-registry-host> <aws-region>
set -euo pipefail

readonly APP_DIR=/opt/livocrm
readonly SHA="${1:?usage: deploy.sh <sha> <registry> <region>}"
readonly REGISTRY="${2:?usage: deploy.sh <sha> <registry> <region>}"
readonly REGION="${3:?usage: deploy.sh <sha> <registry> <region>}"

if [[ ! "$SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "deploy.sh: first argument must be a full 40-character commit sha" >&2
  exit 2
fi

cd "$APP_DIR"
git fetch --quiet origin
git checkout --quiet --detach "$SHA"

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

export IMAGE_TAG="$SHA" ECR_REGISTRY="$REGISTRY"
compose=(docker compose -f docker-compose.yml -f cloud/deploy/docker-compose.prod.yml)
"${compose[@]}" pull backend frontend
"${compose[@]}" up -d --no-build --wait --remove-orphans
docker image prune -f --filter "until=168h" >/dev/null
echo "deployed ${SHA}"
