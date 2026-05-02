#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

rm -rf mees-shared-py mees-shared-ui
cp -r ../mees-shared-py .
cp -r ../mees-shared-ui .
rm -rf mees-shared-py/.git mees-shared-ui/.git mees-shared-ui/node_modules

podman build -t mcp-admin:latest .

rm -rf mees-shared-py mees-shared-ui
