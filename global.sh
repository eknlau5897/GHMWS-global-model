PYTHON_CMD="python3.11" # Or "python"
SCRIPT_PATH="global.py"

echo "=== GHMWS Automation Started ==="

while true
do
    git pull origin main
    # 1. Calculate the latest cycle (00z or 12z)
    CURRENT_HOUR=$(date -u +"%H")
    if [ "$CURRENT_HOUR" -lt 09 ]; then
        # Before 09 UTC, the 12z from yesterday is the safest "latest"
        RUN_DATE=$(date -u -v-1d +"%Y%m%d12")
    elif [ "$CURRENT_HOUR" -lt 21 ]; then
        # Between 09 and 21 UTC, try today's 00z
        RUN_DATE=$(date -u +"%Y%m%d00")
    else
        # After 21 UTC, try today's 12z
        RUN_DATE=$(date -u +"%Y%m%d12")
    fi

    echo "Targeting Run: $RUN_DATE"

    # 2. Run Python
    $PYTHON_CMD $SCRIPT_PATH $RUN_DATE

    PYTHON_STATUS=$?

    # 3. Check Result
    if [ $PYTHON_STATUS -eq 0 ]; then
        echo "Run $RUN_DATE complete. Updating Git..."
        
        git add .
        git commit -m "Auto update for $RUN_DATE"
        git push origin main
        
        echo "Sleeping for 12 hours..."
        sleep 43200
    else
        echo "Error or data not ready for $RUN_DATE. Retrying in 10 minutes..."
        sleep 600
    fi
done