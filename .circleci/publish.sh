#!/bin/sh
set -e

poetry build
poetry publish
