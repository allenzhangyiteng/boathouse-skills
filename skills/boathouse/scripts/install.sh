#!/bin/sh
# Installs the public Boat House CLI; does not connect an account or deploy.
set -eu
installer=$(mktemp)
trap 'rm -f "$installer"' EXIT HUP INT TERM
curl -fsSL https://boathousecloud.com/install.sh -o "$installer"
sh "$installer"
