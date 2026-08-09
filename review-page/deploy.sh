#!/usr/bin/env bash
# Deploy the review page.
#
# Why this script instead of `cd dist && vercel deploy`:
# the Vercel CLI resolves the enclosing *git repository root* as the upload
# source, not the directory you run it from. Running it inside the repo
# therefore uploads the whole project — including ocr-pipeline/.env and the
# scanned pages — and serves nothing at / because there's no index.html at
# that root. This stages only the built page in a clean directory outside
# any git repo, so there is nothing else available to upload.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE="${TMPDIR:-/tmp}/navya-review-deploy"

if [ ! -f "$HERE/dist/index.html" ]; then
  echo "dist/index.html missing — run build_review.py first" >&2
  exit 1
fi

rm -rf "$STAGE"
mkdir -p "$STAGE"
cp "$HERE/dist/index.html" "$HERE/dist/vercel.json" "$STAGE/"
[ -f "$HERE/dist/round2.html" ] && cp "$HERE/dist/round2.html" "$STAGE/"

# Belt and braces: refuse to deploy if anything sensitive slipped in.
if find "$STAGE" -name '.env*' -o -name '*.pem' -o -name '*.key' | grep -q .; then
  echo "refusing to deploy: secret-looking file in staging dir" >&2
  exit 1
fi

echo "staging $(find "$STAGE" -type f | wc -l | tr -d ' ') file(s) from $STAGE:"
find "$STAGE" -type f -exec basename {} \; | sed 's/^/  /'

cd "$STAGE"
npx --yes vercel@latest deploy --prod --yes
