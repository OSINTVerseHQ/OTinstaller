#!/bin/bash
set -e
cd /home/otinstaller
source .venv/bin/activate
export OTINSTALLER_HOME=$(mktemp -d)
echo "OTINSTALLER_HOME=$OTINSTALLER_HOME"
otinstaller init --yes > /dev/null 2>&1
otinstaller install sherlock maigret --yes > /dev/null 2>&1
echo "=== auto example.com --dry-run ==="
otinstaller auto example.com --dry-run 2>&1
otinstaller remove --all --yes > /dev/null 2>&1