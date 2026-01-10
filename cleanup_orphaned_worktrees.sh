#!/bin/bash
# cleanup_orphaned_worktrees.sh

MAIN_REPO=$1

cd "$MAIN_REPO" || exit 1

# List all registered worktrees
git worktree list --porcelain | grep '^worktree ' | while read -r line; do
    worktree_path=$(echo "$line" | cut -d' ' -f2)

    # If the directory doesn't exist anymore
    if [ ! -d "$worktree_path" ]; then
        # Extract branch name from .git/worktrees/<name>/gitdir or HEAD
        wt_name=$(basename "$worktree_path")
        echo "Removing orphaned worktree: $wt_name"
        git worktree remove --force "$wt_name" 2>/dev/null || true
    fi
done

git branch --merged | grep '^debug/' | xargs -r git branch -D
