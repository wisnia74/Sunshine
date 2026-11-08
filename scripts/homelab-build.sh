#!/bin/bash
set -eo pipefail

version=${1:?usage: scripts/homelab-build.sh <version, e.g. 2026.1103.235308>}
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
[ -z "$(git status --porcelain)" ] || { echo "Commit or stash your changes first." >&2; exit 1; }
commit=$(git rev-parse HEAD)
echo "Building $version from $commit ($(git log -1 --format=%s))"

docker build -f docker/debian.dockerfile --target sunshine \
  --build-arg BASE=ubuntu --build-arg TAG=26.04 \
  --build-arg BRANCH="$(git branch --show-current)" --build-arg COMMIT="$commit" \
  --build-arg BUILD_VERSION="$version" -t wisnia74/sunshine .

rm -rf artifacts && mkdir artifacts
docker rm -f sunshine-extract >/dev/null 2>&1 || true
docker create --name sunshine-extract wisnia74/sunshine >/dev/null
docker cp sunshine-extract:/artifacts/. artifacts/
docker rm sunshine-extract >/dev/null
ls -l artifacts/*.deb
