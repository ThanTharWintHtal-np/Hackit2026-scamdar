#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$repo_root/backend" && python -m unittest discover -s tests -v)
(cd "$repo_root/backend" && pytest -q)
(cd "$repo_root/frontend" && npm test && npm run build)
