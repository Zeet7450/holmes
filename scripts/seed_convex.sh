#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx convex import --table cities --append -y data/seed/convex-import/cities.jsonl
npx convex import --table variables --append -y data/seed/convex-import/variables.jsonl
npx convex import --table cases --append -y data/seed/convex-import/cases.jsonl
npx convex import --table fires --append -y data/seed/convex-import/fires.jsonl
npx convex import --table cityTrends --append -y data/seed/convex-import/cityTrends.jsonl
echo "Convex seed complete"
