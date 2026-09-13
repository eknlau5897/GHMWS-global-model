#!/bin/bash

# ==============================================================================
# CONFIGURATION & ENVIRONMENT SETUP
# ==============================================================================
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
export HOME="/Users/eknlau"

PROJECT_DIR="/Users/eknlau/VS_code/GHMWS-global-model"
PYTHON_CMD="/opt/anaconda3/bin/python"
SCRIPT_NAME="${PROJECT_DIR}/global.py"

cd "$PROJECT_DIR" || exit 1

# ==============================================================================
# CORE PIPELINE FUNCTION
# ==============================================================================
run_global_pipeline() {
    echo "=================================================================="
    echo "   GHMWS GLOBAL MODEL PIPELINE DAEMON                             "
    echo "=================================================================="
    echo "=== GHMWS Execution Started: $(date -u +"%Y-%m-%d %H:%M:%S UTC") ==="

    # TIME MAPPING: 10Z -> 00Z run, 22Z -> 12Z run
    CURRENT_HOUR=$(date -u +"%H")

    if [ "$CURRENT_HOUR" -ge 10 ] && [ "$CURRENT_HOUR" -lt 22 ]; then
        # Between 10:00 UTC and 21:59 UTC: target today's 00Z initialization
        RUN_DATE=$(date -u +"%Y%m%d00")
    else
        # Between 22:00 UTC and 09:59 UTC: target 12Z initialization
        if [ "$CURRENT_HOUR" -lt 10 ]; then
            # Early morning (00:00–09:59 UTC) targets yesterday's 12Z initialization
            RUN_DATE=$(date -u -v-1d +"%Y%m%d12" 2>/dev/null || date -u -d "yesterday" +"%Y%m%d12")
        else
            # 22:00–23:59 UTC targets today's 12Z initialization
            RUN_DATE=$(date -u +"%Y%m%d12")
        fi
    fi

    echo "🧹 Cleaning untracked data..."
    git clean -fdX

    echo "Targeting Run: $RUN_DATE"

    # Run Python script
    if $PYTHON_CMD "$SCRIPT_NAME" "$RUN_DATE"; then
        echo "✅ Python execution successful. Pushing results to Git..."
        
        git checkout --orphan temp_branch 2>/dev/null || git checkout temp_branch
        git add -A
        git commit -m "Reset history to latest version: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" || echo "No changes to commit."
        git branch -D main 2>/dev/null
        git branch -m main
        git push -f origin main
    else
        echo "⚠️ Python script or plot failed with exit code $?. Skipping Git push, proceeding to next cycle."
    fi

    echo "=== GHMWS Execution Finished: $(date -u +"%Y-%m-%d %H:%M:%S UTC") ==="
}

# ==============================================================================
# SLEEP CALCULATION HELPERS (Calculates target sleep to 10:00 UTC or 22:00 UTC)
# ==============================================================================
get_seconds_until_next_target_run() {
    $PYTHON_CMD -c '
import datetime

now = datetime.datetime.now(datetime.timezone.utc)
today = now.date()

# Target run windows: 10:00 UTC and 22:00 UTC
target_10 = datetime.datetime(today.year, today.month, today.day, 10, 0, 0, tzinfo=datetime.timezone.utc)
target_22 = datetime.datetime(today.year, today.month, today.day, 22, 0, 0, tzinfo=datetime.timezone.utc)
tomorrow_10 = target_10 + datetime.timedelta(days=1)

# Find next upcoming target timestamp
if now < target_10:
    next_target = target_10
elif now < target_22:
    next_target = target_22
else:
    next_target = tomorrow_10

seconds_remaining = int((next_target - now).total_seconds())

# Safety buffer: If execution ends < 10 mins (600s) before target, jump to the following target
if seconds_remaining < 600:
    if next_target == target_10:
        next_target = target_22
    elif next_target == target_22:
        next_target = tomorrow_10
    else:
        next_target += datetime.timedelta(hours=12)
    seconds_remaining = int((next_target - now).total_seconds())

print(seconds_remaining)
'
}

# ==============================================================================
# DAEMON SCHEDULER LOOP
# ==============================================================================
echo "🚀 Global Model Daemon active (Targeting 10Z and 22Z runs). Running in 1 shell..."

while true; do
    # 1. Run main pipeline
    run_global_pipeline

    # 2. Compute exact sleep duration until the next 10Z or 22Z mark
    SLEEP_SECS=$(get_seconds_until_next_target_run)

    # Fallback safety guard (ensure integer > 10 min)
    if ! [[ "$SLEEP_SECS" =~ ^[0-9]+$ ]] || [ "$SLEEP_SECS" -lt 600 ]; then
        echo "⚠️ Target calculation fallback triggered. Sleeping for 12 hours."
        SLEEP_SECS=43200
    fi

    HOURS=$(awk "BEGIN {printf \"%.2f\", $SLEEP_SECS/3600}")
    
    echo "⏳ Sleeping $SLEEP_SECS seconds (~$HOURS hours) until next target run..."
    sleep "$SLEEP_SECS"
done