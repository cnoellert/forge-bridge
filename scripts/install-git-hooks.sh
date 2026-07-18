#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [ ! -x .githooks/pre-commit ]; then
  printf 'error: .githooks/pre-commit is missing or not executable\n' >&2
  exit 1
fi

git config --local core.hooksPath .githooks
printf 'forge-bridge git hooks enabled via core.hooksPath=.githooks\n'
