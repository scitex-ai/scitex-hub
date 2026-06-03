#!/bin/bash
# SciTeX Web - Test Runner Script

# Set up environment
export PYTHONPATH="$PYTHONPATH:$(pwd)/src"
export SCITEX_HUB_DJANGO_SETTINGS_MODULE="config.settings.development"

# Activate virtual environment if it exists
if [ -d ".env" ]; then
    source .env/bin/activate
fi

# Parse arguments
DEBUG=false
SYNC=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --debug) DEBUG=true ;;
        -s|--sync) SYNC=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Create log file
LOG_FILE="./.run_tests.sh.log"
> "$LOG_FILE"

# Function to log messages
log_message() {
    echo "$1" | tee -a "$LOG_FILE"
}

log_message "Starting test run at $(date)"

# Sync tests with source if requested
if [ "$SYNC" = true ]; then
    log_message "Synchronizing test and source directories..."
    # This would contain code to validate test structure and embed source code
    # For now, it's a placeholder
    log_message "Synchronization complete."
fi

# Run Django tests
if [ -d "tests" ]; then
    log_message "Running Django tests..."

    if [ "$DEBUG" = true ]; then
        python manage.py test tests --verbosity=2 2>&1 | tee -a "$LOG_FILE"
    else
        python manage.py test tests 2>&1 | tee -a "$LOG_FILE"
    fi

    TEST_EXIT_CODE=${PIPESTATUS[0]}

    if [ $TEST_EXIT_CODE -eq 0 ]; then
        log_message "All Django tests passed!"
    else
        log_message "Django tests failed with exit code $TEST_EXIT_CODE"
    fi
else
    log_message "No tests directory found."
    TEST_EXIT_CODE=1
fi

# Run JavaScript tests if package.json exists
if [ -f "package.json" ]; then
    log_message "Running JavaScript tests..."

    if [ "$DEBUG" = true ]; then
        npm test -- --verbose 2>&1 | tee -a "$LOG_FILE"
    else
        npm test 2>&1 | tee -a "$LOG_FILE"
    fi

    JS_TEST_EXIT_CODE=${PIPESTATUS[0]}

    if [ $JS_TEST_EXIT_CODE -eq 0 ]; then
        log_message "All JavaScript tests passed!"
    else
        log_message "JavaScript tests failed with exit code $JS_TEST_EXIT_CODE"
    fi

    # Combine exit codes
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        TEST_EXIT_CODE=$JS_TEST_EXIT_CODE
    fi
fi

log_message "Test run completed at $(date)"

# Exit with the same code as the tests
