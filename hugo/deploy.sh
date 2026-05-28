#!/usr/bin/env bash

set -euo pipefail

main() {
  local branch="${1:?Usage: deploy.sh <branch>}"

  echo "Deploying branch: ${branch}..."
  npx wrangler deploy
}

main "$@"
