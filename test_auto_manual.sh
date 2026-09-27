#!/bin/bash
set -e
cd /home/otinstaller
source .venv/bin/activate
export OTINSTALLER_HOME=$(mktemp -d)
echo "OTINSTALLER_HOME=$OTINSTALLER_HOME"
otinstaller init --yes
otinstaller install sherlock maigret --yes
echo "--- auto someexampleuser123 --dry-run ---"
otinstaller auto someexampleuser123 --dry-run
echo "--- auto octocat --parallel 2 --yes ---"
otinstaller auto octocat --parallel 2 --yes
echo "--- auto example.com --dry-run ---"
otinstaller auto example.com --dry-run
echo "--- remove all ---"
otinstaller remove --all --yes