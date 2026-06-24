#!/usr/bin/env bash
#
# Install forge-bridge's tracked git hooks into this checkout's .git/hooks.
#
# Hooks aren't shared by `git clone`, so each checkout runs this once. It symlinks
# the tracked source (scripts/git-hooks/*) into .git/hooks so edits to the tracked
# hook take effect immediately, with no copy to keep in sync.
#
# Safe to re-run (idempotent). Respects an existing core.hooksPath if you've set one.
#
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
src_dir="${repo_root}/scripts/git-hooks"
hooks_dir="$(git rev-parse --git-path hooks)"

mkdir -p "$hooks_dir"

for src in "$src_dir"/*; do
    [ -e "$src" ] || continue
    name="$(basename "$src")"
    dest="${hooks_dir}/${name}"
    if [ -e "$dest" ] && [ ! -L "$dest" ]; then
        echo "  ! ${dest} exists and is not a symlink — leaving it alone (move it aside and re-run)." >&2
        continue
    fi
    ln -sf "$src" "$dest"
    chmod +x "$src"
    echo "  ✓ linked ${name} -> ${src}"
done

echo "Git hooks installed into ${hooks_dir}."
