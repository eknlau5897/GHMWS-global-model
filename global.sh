#!/bin/bash
set -e

# ==============================================================================
# INITIAL ENVIRONMENT SETUP
# ==============================================================================
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
export HOME="/Users/eknlau"

while true; do
    # Capture current Unix timestamp based strictly on UTC time
    NOW=$(date -u +%s)
    
    # Get date strings in UTC
    YMD_TODAY=$(date -u +"%Y-%m-%d")
    YMD_TOMORROW=$(date -u -v+1d +"%Y-%m-%d")

    # Define all 4 possible targets explicitly
    T1=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TODAY 10:00:00" +%s)
    T2=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TODAY 22:00:00" +%s)
    T3=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TOMORROW 10:00:00" +%s)
    T4=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TOMORROW 22:00:00" +%s)

    # Filter targets to only those in the future, then pick the earliest one
    NEXT_TARGET=$(printf "%s\n" "$T1" "$T2" "$T3" "$T4" | awk -v now="$NOW" '$1 > now' | sort -n | head -n1)
    
    # Calculate difference in seconds
    SECONDS_TO_WAIT=$((NEXT_TARGET - NOW))
    
    # Format target date display string for your log
    TARGET_DATE_STRING=$(date -u -r "$NEXT_TARGET" +"%Y-%m-%d %H:%M:%S UTC")

    echo "⏱️ Waiting $SECONDS_TO_WAIT seconds until the next fixed target: $TARGET_DATE_STRING"
    
    # Force the machine to pause execution until the fixed target time hits
    sleep "${SECONDS_TO_WAIT}s"

    echo "=================================================================="
    echo "   GHMWS GLOBAL MODEL PIPELINE DAEMON                             "
    echo "=================================================================="
    echo "=== GHMWS Execution Started: $(date) ==="

    # ==============================================================================
    # PIPELINE EXECUTION
    # ==============================================================================
    PROJECT_DIR="/Users/eknlau/VS_code/GHMWS"
    PYTHON_CMD="/opt/anaconda3/bin/python"
    SCRIPT_NAME="/Users/eknlau/VS_code/GHMWS-global-model/global.py"

    cd "$PROJECT_DIR" || exit 1

    git pull origin main

    # Use the static NEXT_TARGET time to determine RUN_DATE rather than execution drift time
    CURRENT_HOUR=$(date -u -r "$NEXT_TARGET" +"%H")
    if [ "$CURRENT_HOUR" -eq 10 ]; then
        RUN_DATE=$(date -u -r "$NEXT_TARGET" +"%Y%m%d00")
    else
        RUN_DATE=$(date -u -r "$NEXT_TARGET" +"%Y%m%d12")
    fi

    echo "Targeting Run: $RUN_DATE"

    # Run Python and pipe log output cleanly
    set +e
    $PYTHON_CMD "$SCRIPT_NAME" "$RUN_DATE"
    PYTHON_STATUS=$?
    set -e

    if [ $PYTHON_STATUS -eq 0 ]; then
        echo "Run $RUN_DATE complete. Updating Git..."
        git add .
        # Added a conditional check so git commit doesn't fail if nothing changed
        git diff-index --quiet HEAD || git commit -m "Auto update maps for Run $RUN_DATE"
        git push origin main --force
    else
        echo "Run $RUN_DATE failed. Skipping Git updates."
    fi

    echo "=== GHMWS Execution Finished ==="
    
    # Small breathing room before starting the next time calculation cycle
    sleep 2s
done