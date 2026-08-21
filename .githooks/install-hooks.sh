#!/bin/bash
# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
#
# Install git hooks for vibey-bootstrap
#
# This script configures git to use the hooks in .githooks/

set -e

echo "🔧 Installing git hooks..."

# Get the git directory
GIT_DIR=$(git rev-parse --git-dir)

# Configure git to use .githooks directory
git config core.hooksPath .githooks

# Make hooks executable (Unix/Mac/Git Bash)
chmod +x .githooks/pre-commit 2>/dev/null || true
chmod +x .githooks/pre-push 2>/dev/null || true

echo "✅ Git hooks installed successfully!"
echo ""
echo "The following hooks are now active:"
echo "  - pre-commit: Runs quality checks before each commit"
echo "  - pre-push: Runs comprehensive tests before push"
echo ""
echo "To skip hooks (not recommended):"
echo "  git commit --no-verify"
echo "  git push --no-verify"
