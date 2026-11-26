#!/usr/bin/env bash
# Copy the long-text Hungarian translations (not published in the public repo) into the private
# companion repository ../pack-texts and commit them. pack/ stays the single source of truth.
set -euo pipefail
cd "$(dirname "$0")"
DEST=../pack-texts
FILES=(fulltext/translations/definitions-0[1-9].json fulltext/translations/health-0[1-3].json
       fulltext/translations/labels-and-quizzes-0[12].json fulltext/translations/auto-core.json
       fulltext/merged/field-translations.json fulltext/merged/translated-units.json fulltext/merged/coverage.json
       corrections/fulltext-approved.json)
mkdir -p "$DEST"
[ -d "$DEST/.git" ] || git -C "$DEST" init -q -b main
for f in "${FILES[@]}"; do mkdir -p "$DEST/$(dirname "$f")"; cp -p "$f" "$DEST/$f"; done
git -C "$DEST" add -A
git -C "$DEST" diff --cached --quiet || git -C "$DEST" commit -q -m "${1:-Sync long-text translations from pack @ $(git rev-parse --short HEAD 2>/dev/null || echo uncommitted)}"
git -C "$DEST" log --oneline -1
