#!/bin/bash

# Define absolute paths and change to your working directory
PROJECT_DIR="/Users/eknlau/VS_code/GHMWS"
PYTHON_CMD="/opt/anaconda3/bin/python3.11"
SCRIPT_PATH="./global.py"

cd "$PROJECT_DIR" || exit 1

echo "=== GHMWS Cron Execution Started: $(date) ==="

# Fetch latest changes before checking/running
git pull origin main

# 1. Calculate the latest cycle (00z or 12z)
CURRENT_HOUR=$(date -u +"%H")
if [ "$CURRENT_HOUR" -lt 09 ]; then
    RUN_DATE=$(date -u -v-1d +"%Y%m%d12")
elif [ "$CURRENT_HOUR" -lt 21 ]; then
    RUN_DATE=$(date -u +"%Y%m%d00")
else
    RUN_DATE=$(date -u +"%Y%m%d12")
fi

echo "Targeting Run: $RUN_DATE"

# 2. Run Python
python3.11 $SCRIPT_PATH $RUN_DATE
PYTHON_STATUS=$?

# 3. Check Result and Sync Git
if [ $PYTHON_STATUS -eq 0 ]; then
    echo "Run $RUN_DATE complete. Updating Git..."
else
    echo "Run $RUN_DATE failed. Stashing partial results to Git..."
fi

git add .
git commit -m "Auto update for $RUN_DATE"
git push origin main

echo "=== GHMWS Cron Execution Finished ==="