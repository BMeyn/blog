#!/usr/bin/env bash
#
# Install git hooks for this repository
#
# This script creates symlinks from .git/hooks/ to scripts/hooks/
# so that the hooks are version-controlled and shared across the team.
#

set -e  # Exit immediately if a command exits with a non-zero status

# Get the repository root directory
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="${REPO_ROOT}/scripts/hooks"
HOOKS_DST="${REPO_ROOT}/.git/hooks"

# Ensure we're in a git repository
if [ ! -d "${REPO_ROOT}/.git" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Ensure source hooks directory exists
if [ ! -d "$HOOKS_SRC" ]; then
    echo "Error: Hooks source directory not found: $HOOKS_SRC"
    exit 1
fi

# Create .git/hooks directory if it doesn't exist
mkdir -p "$HOOKS_DST"

echo "Installing git hooks..."

# Install pre-commit hook
HOOK_NAME="pre-commit"
SRC_HOOK="${HOOKS_SRC}/${HOOK_NAME}"
DST_HOOK="${HOOKS_DST}/${HOOK_NAME}"

if [ ! -f "$SRC_HOOK" ]; then
    echo "Warning: ${HOOK_NAME} hook not found in ${HOOKS_SRC}"
else
    # Remove existing hook if present (file or symlink)
    if [ -L "$DST_HOOK" ] || [ -f "$DST_HOOK" ]; then
        rm "$DST_HOOK"
    fi

    # Create symlink (relative path for portability)
    ln -s "../../scripts/hooks/${HOOK_NAME}" "$DST_HOOK"

    # Ensure source hook is executable
    chmod +x "$SRC_HOOK"

    echo "  ✓ Installed ${HOOK_NAME} hook"
fi

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will now automatically run translate.py on"
echo "staged markdown files in _posts/ before each commit."
echo ""
echo "To bypass the hook temporarily, use: git commit --no-verify"
