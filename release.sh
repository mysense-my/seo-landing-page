#!/bin/zsh
# Stamp a fresh cache-buster into index.html, then commit and push.
#
# This exists because of a real bug: the first two deploys both shipped
# `?v=1`, so returning browsers kept serving the FIRST deploy's CSS and the
# second deploy's changes were invisible on the live site while being perfectly
# fine in a cache-disabled test. Never push a CSS or JS change without running
# this.
set -e
cd "$(dirname "$0")"
V=$(date +%s)
/usr/bin/sed -i '' -E "s/(\.(css|js))\?v=[0-9]+/\1?v=$V/g" index.html
git add -A
git commit -q -m "${1:-Update}

Cache-buster stamped to v=$V.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push
echo "pushed at v=$V"
