#!/bin/bash

set -eo pipefail

# check we're on master
HEAD_HASH=$(git rev-parse HEAD)
MASTER_HASH=$(git rev-parse master)

if [ "$HEAD_HASH" != "$MASTER_HASH" ]; then
	echo "You're not on master!" 1>&2
	exit 1
fi

poetry version "$1"
NEW_VERSION=$(poetry version -s)

git add pyproject.toml
git commit -m "v${NEW_VERSION}"
git tag -a "v${NEW_VERSION}" -m "v${NEW_VERSION}"

git push --follow-tags
