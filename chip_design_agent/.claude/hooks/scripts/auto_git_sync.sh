#!/bin/bash
# auto_git_sync.sh
# SessionEnd hook: auto-commit and push changes to agent/skill/command files.
# Uses --no-verify on commit to prevent recursive hook triggering.

set -e

# Navigate to git root
REPO_DIR="$(git -C "$(dirname "$0")/../../../.." rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_DIR" ]; then
    exit 0
fi
cd "$REPO_DIR"

# Define monitored paths (relative to git root)
MONITORED_PATHS=(
    "agents/config/"
    "skills/"
    ".claude/agents/"
    ".claude/skills/"
    ".claude/commands/"
    ".claude/settings.json"
)

# Collect changed files in monitored paths (unstaged + staged + untracked)
# Exclude settings.local.json which is gitignored
CHANGED=$( (
    git diff --name-only HEAD
    git diff --cached --name-only
    git ls-files --others --exclude-standard
) | sort -u | grep -v '.claude/settings.local.json' )

if [ -z "$CHANGED" ]; then
    exit 0
fi

# Check if any change falls under a monitored path
HAS_MONITORED=false
for path in "${MONITORED_PATHS[@]}"; do
    if echo "$CHANGED" | grep -q "^${path}"; then
        HAS_MONITORED=true
        break
    fi
done

if [ "$HAS_MONITORED" = false ]; then
    exit 0
fi

# Stage all changes in monitored directories/files
# git add -A handles all states: modified, added, deleted, untracked
for path in "${MONITORED_PATHS[@]}"; do
    git add -A -- "$path" 2>/dev/null || true
done

# Check if anything was actually staged
STAGED=$(git diff --cached --name-only)
if [ -z "$STAGED" ]; then
    exit 0
fi

git -c user.name="Claude Code" -c user.email="noreply@anthropic.com" commit --no-verify -m "$(cat <<'EOF'
chore: auto-sync agent/skill/command updates

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Push if remote exists (non-blocking: skip credential prompt)
if git remote -v | grep -q '^origin'; then
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=echo git push --no-verify origin "$CURRENT_BRANCH" 2>/dev/null || true
fi

exit 0
