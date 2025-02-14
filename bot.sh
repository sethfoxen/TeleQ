#!/bin/bash

# Wait 60 seconds after start up, to ensure Pi has booted fully
sleep 1

# Get the directory of the bash script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Construct the relative path to the Python script
RELATIVE_PATH="bot.py"

# Construct the absolute path to the Python script
ABSOLUTE_PATH="${SCRIPT_DIR}/${RELATIVE_PATH}"

# Check if the Python script exists
if [ -f "${ABSOLUTE_PATH}" ]; then
  # Run the Python script
  python3 "${ABSOLUTE_PATH}"
else
  echo "Error: Python script not found at ${ABSOLUTE_PATH}"
  exit 1
fi
