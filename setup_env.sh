#!/bin/bash
find_free_port() {
    comm -23 <(seq 4100 4200) <(ss -tan | awk '{print $4}' | cut -d':' -f2 | sort | uniq) | head -1
}


CORR_ID=$1
if [ -z "$CORR_ID" ]; then
    echo "Error: No correlation ID provided."
    exit 1
fi

# Fetch prod commit hash (replace with your method)
PROD_HASH=$(eval "$GET_PROD_HASH_COMMAND")
if [ -z "$PROD_HASH" ]; then
    PROD_HASH=$(git rev-parse HEAD)  # Fallback to current HEAD if unavailable
fi

# Compare with current master
cd "${PROJECT_PATH}" || { echo "Error: Cannot cd to ${PROJECT_PATH}"; exit 1; }
git fetch origin master  # Update local master ref
MASTER_HASH=$(git rev-parse origin/master)
if [ "$PROD_HASH" = "$MASTER_HASH" ]; then
    COMPARE_ADVICE="The error occurred on the latest master commit—no newer fixes available."
    MATCHES_MASTER=true
else
    COMPARE_ADVICE="The error occurred on commit $PROD_HASH. Compare with current master ($MASTER_HASH) to see if the bug is already fixed (e.g., git diff $PROD_HASH..$MASTER_HASH)."
    MATCHES_MASTER=false
fi

# Create worktree at prod hash
WORKTREE_DIR="${WORKTREE_BASE}/${CORR_ID}"
mkdir -p "$(dirname "$WORKTREE_DIR")"
git worktree add "$WORKTREE_DIR" "$PROD_HASH" -b "debug/${CORR_ID}" || {
    echo "Error creating worktree. Check if branch exists or commit is valid."
    exit 1
}

# Copy safe dev env
cp "$PROJECT_PATH"/"$DEBUG_ENV" "$WORKTREE_DIR/.env"

# Start OpenCode
cd "$WORKTREE_DIR"
PORT=$(find_free_port 4100)  # Implement find_free_port as before
opencode serve --port $PORT --hostname 127.0.0.1 --no-mdns > server.log 2>&1 &
echo $! > /tmp/opencode-pid-${CORR_ID}

# Output to n8n
echo "{\"port\": $PORT, \"worktree\": \"$WORKTREE_DIR\", \"prod_hash\": \"$PROD_HASH\", \"compare_advice\": \"$COMPARE_ADVICE\", \"matches_master\": $MATCHES_MASTER}"
