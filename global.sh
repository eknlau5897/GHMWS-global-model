#!/bin/bash
set -e

# ==============================================================================
# INITIAL ENVIRONMENT SETUP
# ==============================================================================
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
export HOME="/Users/eknlau"

FIRST_RUN=true

while true; do
    NOW=$(date -u +%s)

    if [ "$FIRST_RUN" = true ]; then
        echo "🚀 Running immediately on startup..."
        
        CURRENT_HOUR=$(date -u +"%H")
        
        # Determine RUN_DATE based on current time
        # If between 10Z and 21Z -> Today's 00Z
        # If >= 22Z -> Today's 12Z
        # If < 10Z -> Yesterday's 12Z
        CURRENT_HOUR=$(date -u +"%H")

        if [ "$CURRENT_HOUR" -ge 10 ] && [ "$CURRENT_HOUR" -lt 22 ]; then
            # Between 10Z and 21Z -> Run Today's 00Z
            RUN_DATE=$(date -u +"%Y%m%d00")
        elif [ "$CURRENT_HOUR" -ge 22 ]; then
            # 22Z or later -> Run Today's 12Z
            RUN_DATE=$(date -u +"%Y%m%d12")
        else
            RUN_DATE=$(date -u -v-1d +"%Y%m%d12")
        fi

        FIRST_RUN=false
    else
        # Define target timestamps for scheduled runs
        YMD_TODAY=$(date -u +"%Y-%m-%d")
        YMD_TOMORROW=$(date -u -v+1d +"%Y-%m-%d")

        T1=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TODAY 10:00:00" +%s)
        T2=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TODAY 22:00:00" +%s)
        T3=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TOMORROW 10:00:00" +%s)
        T4=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TOMORROW 22:00:00" +%s)

        # Filter targets to only those in the future, then pick the earliest one
        NEXT_TARGET=$(printf "%s\n" "$T1" "$T2" "$T3" "$T4" | awk -v now="$NOW" '$1 > now' | sort -n | head -n1)
        
        SECONDS_TO_WAIT=$((NEXT_TARGET - NOW))
        TARGET_DATE_STRING=$(date -u -r "$NEXT_TARGET" +"%Y-%m-%d %H:%M:%S UTC")

        echo "⏱️ Waiting $SECONDS_TO_WAIT seconds until next schedule: $TARGET_DATE_STRING"
        sleep "${SECONDS_TO_WAIT}s"

        # Determine RUN_DATE for scheduled runs
        TARGET_HOUR=$(date -u -r "$NEXT_TARGET" +"%H")
        if [ "$TARGET_HOUR" -eq 10 ]; then
            RUN_DATE=$(date -u -r "$NEXT_TARGET" +"%Y%m%d00")
        else
            # Plots target date's 12Z without subtracting a day (-v-1d removed)
            RUN_DATE=$(date -u -r "$NEXT_TARGET" +"%Y%m%d12")
        fi
    fi

    echo "=================================================================="
    echo "   GHMWS GLOBAL MODEL PIPELINE DAEMON                             "
    echo "=================================================================="
    echo "=== GHMWS Execution Started: $(date) ==="

    # ==============================================================================
    # PIPELINE EXECUTION & STORAGE CLEANUP
    # ==============================================================================
    PROJECT_DIR="/Users/eknlau/VS_code/GHMWS-global-model"
    PYTHON_CMD="/opt/anaconda3/bin/python"
    SCRIPT_NAME="/Users/eknlau/VS_code/GHMWS-global-model/global.py"

    cd "$PROJECT_DIR" || exit 1

    echo "🧹 Cleaning untracked data, cache, and old output files..."
    git clean -fdX  # Removes ignored/untracked files (caches, temp outputs)
    git gc --prune=now --aggressive  # Cleans up Git's local object store to free disk space

    echo "Targeting Run: $RUN_DATE"

    # Run Python script
    set +e
    $PYTHON_CMD "$SCRIPT_NAME" "$RUN_DATE"
    PYTHON_STATUS=$?
    
    # Reset git history to single commit and push
    git checkout --orphan temp_branch
    git add -A
    git commit -m "Reset history to latest version: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" || echo "No changes to commit."
    git branch -D main
    git branch -m main
    git push -f origin main
    set -e
    
    echo "=== GHMWS Execution Finished ==="
done