#!/bin/bash
set -e

# ==============================================================================
# INITIAL ENVIRONMENT SETUP
# ==============================================================================
# Prevent the Mac from sleeping as long as this script process is alive

# Expose system paths so background processes can find git, curl, and python
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
export HOME="/Users/eknlau"

# Infinite loop that calculates the next run time, sleeps, and executes
while true; do
    # Capture current Unix timestamp based strictly on UTC time
    NOW=$(date -u +%s)
    
    # Get current and tomorrow date strings in UTC
    YMD_TODAY=$(date -u +"%Y-%m-%d")
    YMD_TOMORROW=$(date -v+1d -u +"%Y-%m-%d")

    # Define targets explicitly locked to 10Z and 22Z in the UTC timezone
    T1=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TODAY 10:00:00" +%s)
    T2=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TODAY 22:00:00" +%s)

    # If a specific target hour has already passed in UTC, advance it to tomorrow UTC
    [ $NOW -ge $T1 ] && T1=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TOMORROW 10:00:00" +%s)
    [ $NOW -ge $T2 ] && T2=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$YMD_TOMORROW 22:00:00" +%s)

    # Sort array of upcoming timestamps to find the absolute closest next target
    NEXT_TARGET=$(printf "%s\n" "$T1" "$T2" | sort -n | head -n1)
    
    # Calculate difference in seconds
    SECONDS_TO_WAIT=$((NEXT_TARGET - NOW))
    
    # Format target date display string for your log
    TARGET_DATE_STRING=$(date -u -r $NEXT_TARGET +"%Y-%m-%d %H:%M:%S UTC")

    echo "⏱️ Waiting $SECONDS_TO_WAIT seconds until the next fixed target: $TARGET_DATE_STRING"
    
    # Force the machine to pause execution until the fixed target time hits
    sleep ${SECONDS_TO_WAIT}s

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

    CURRENT_HOUR=$(date -u +"%H")
    if [ "$CURRENT_HOUR" -lt 09 ]; then
        RUN_DATE=$(date -u -v-1d +"%Y%m%d12")
    elif [ "$CURRENT_HOUR" -lt 21 ]; then
        RUN_DATE=$(date -u +"%Y%m%d00")
    else
        RUN_DATE=$(date -u +"%Y%m%d12")
    fi

    echo "Targeting Run: $RUN_DATE"

    # Run Python and pipe log output cleanly (disable set -e briefly to catch failure)
    set +e
    $PYTHON_CMD "$SCRIPT_NAME" "$RUN_DATE"
    PYTHON_STATUS=$?
    set -e

    if [ $PYTHON_STATUS -eq 0 ]; then
        echo "Run $RUN_DATE complete. Updating Git..."
    else
        echo "Run $RUN_DATE failed. Checking updates..."
    fi

    git add .
    git commit -m "Auto update maps for Run $RUN_DATE"
    git push origin main --force

    echo "=== GHMWS Execution Finished ==="
    
    # Small breathing room before starting the next time calculation cycle
    sleep 2s
done