CORR_ID=$1
kill $(cat /tmp/opencode-pid-${CORR_ID})
cd ${PROJECT_PATH} && git worktree remove "${WORKTREE_BASE}/${CORR_ID}" --force
rm /tmp/opencode-pid-${CORR_ID}
