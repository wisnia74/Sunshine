#!/bin/bash
# sunshine-test-build.sh [TAG] [OUTDIR]: builds the checked-out Sunshine branch as the image wisnia74/sunshine:TAG
# (default test) and copies its .deb to OUTDIR (default $STREAM_DEBUG_OUT/sun), leaving artifacts/ and the
# wisnia74/sunshine:latest image of the installed build alone. VERSION defaults to the installed package's version,
# because an unpacked test binary still reads the installed build's files in /usr/share/sunshine.
set -eo pipefail
tag=${1:-test}; out=${2:-${STREAM_DEBUG_OUT:-/tmp/stream-debug}/sun}
version=${VERSION:-$(dpkg-query -W -f '${Version}' sunshine | cut -d- -f1)}
cd "$(dirname "$0")/../.."
[ -z "$(git status --porcelain)" ] || { echo "FAILED: dirty tree"; exit 1; }
branch=$(git branch --show-current)
lvh="$PWD/scripts/homelab-libvirtualhid.patch"
git -C third-party/libvirtualhid apply "$lvh"
trap 'git -C third-party/libvirtualhid apply -R "$lvh"; git checkout -q "$branch"; echo "tree back on $(git branch --show-current)"' EXIT
docker build -f docker/debian.dockerfile --target sunshine --build-arg BASE=ubuntu --build-arg TAG=26.04 \
  --build-arg BRANCH="$branch" --build-arg COMMIT="$(git rev-parse HEAD)" \
  --build-arg BUILD_VERSION="$version" -t "wisnia74/sunshine:$tag" .
rm -rf "$out" && mkdir -p "$out"
docker rm -f "sunshine-$tag" >/dev/null 2>&1 || true
docker create --name "sunshine-$tag" "wisnia74/sunshine:$tag" >/dev/null
docker cp "sunshine-$tag:/artifacts/." "$out/"
docker rm "sunshine-$tag" >/dev/null
ls -l "$out"/*.deb && echo BUILD-DONE
