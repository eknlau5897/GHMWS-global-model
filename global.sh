#!/bin/bash
PROJECT_DIR="/Users/eknlau/VS_code/GHMWS"
PYTHON_CMD="/opt/anaconda3/bin/python"
SCRIPT_NAME="/Users/eknlau/VS_code/GHMWS-global-model/global.py"

cd "$PROJECT_DIR" || exit 1
echo "=== GHMWS Cron Execution Started: $(date) ==="

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

# Run Python and pipe log output cleanly
$PYTHON_CMD "$SCRIPT_NAME" "$RUN_DATE"
PYTHON_STATUS=$?

if [ $PYTHON_STATUS -eq 0 ]; then
    echo "Run $RUN_DATE complete. Updating Git..."
else
    echo "Run $RUN_DATE failed. Checking updates..."
fi

git add .
git commit -m "Auto update maps for Run $RUN_DATE"
git push origin main

echo "=== GHMWS Cron Execution Finished ==="