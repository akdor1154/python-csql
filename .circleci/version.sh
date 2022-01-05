#!/bin/bash

set -eo pipefail

COMPARE_BRANCH="${2:-master}"

# check we're on master
HEAD_HASH=$(git rev-parse HEAD)
MASTER_HASH=$(git rev-parse "${COMPARE_BRANCH}")

if [ "$HEAD_HASH" != "$MASTER_HASH" ]; then
	echo "You're not on ${COMPARE_BRANCH}! Pass a branch name override as \$2 if you really want to version bump from another branch." 1>&2
	exit 1
fi

poetry version "$1"
NEW_VERSION=$(poetry version -s)

git add pyproject.toml
git commit -m "v${NEW_VERSION}"
git tag -a "v${NEW_VERSION}" -m "v${NEW_VERSION}"

git push --follow-tags
