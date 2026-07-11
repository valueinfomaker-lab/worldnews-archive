#!/usr/bin/env zsh
# 정적 사이트를 빌드하고, 변경이 있으면 커밋·푸시한다.
# GitHub Pages(main /docs)가 push 후 자동으로 재배포한다.
set -euo pipefail
cd "$(dirname "$0")/.."

.venv/bin/python -m generator.build

git add docs
if git diff --cached --quiet; then
  echo "변경 없음 — 커밋/푸시 생략"
  exit 0
fi

git commit -m "archive: build $(date +%F)"
git push origin main
echo "배포 완료"
