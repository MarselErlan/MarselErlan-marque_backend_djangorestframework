#!/bin/bash
# Script to update exchange rates
# This script can be used with cron jobs or scheduled tasks

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the management command
python manage.py update_exchange_rates

# Deactivate virtual environment if it was activated
if [ -d "venv" ]; then
    deactivate
fi

