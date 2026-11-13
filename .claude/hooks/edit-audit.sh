#!/bin/bash
# Appends one line per file edit to the tracked audit log.
INPUT=$(cat)
FILE=$(echo "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) edit ${FILE:-unknown}" >> "${CLAUDE_PROJECT_DIR:-.}/.claude/edit-audit.log"
exit 0
