#!/usr/bin/env bash
set -euo pipefail

echo "Installing OpenClaw for Ubuntu via official installer..."
echo "Official command: curl -fsSL https://openclaw.ai/install.sh | bash"

curl -fsSL https://openclaw.ai/install.sh | bash
