#!/bin/bash

# MIT License
#
# Copyright (c) 2025 Tyler Zervas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Claude task-specific wrapper script
# Usage: ./claude-task.sh <task-type> <task-subtype> [additional claude args...]

set -euo pipefail

# Configuration
CONFIG_FILE="/home/vector_weight/Documents/projects/homelab/homelab-infra/.claude/config.json"
PROJECT_ROOT="/home/vector_weight/Documents/projects/homelab/homelab-infra"

# Load configuration
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Configuration file not found: $CONFIG_FILE"
  exit 1
fi

# Function to get model for task
get_model_for_task() {
  local task_type="$1"
  local task_subtype="$2"

  # Extract model from config using jq
  local model
  model=$(jq -r --arg type "$task_type" --arg subtype "$task_subtype" \
    '.models.taskSpecific[$type][$subtype].model // .models.default' "$CONFIG_FILE")

  echo "$model"
}

# Function to get allowed tools for task
get_allowed_tools() {
  jq -r '.allowedTools | join(",")' "$CONFIG_FILE"
}

# Main
if [ $# -lt 2 ]; then
  echo "Usage: $0 <task-type> <task-subtype> [additional claude args...]"
  echo "Example: $0 infrastructure architecture --print 'Design the system architecture'"
  exit 1
fi

TASK_TYPE="$1"
TASK_SUBTYPE="$2"
shift 2

# Get model and tools
MODEL=$(get_model_for_task "$TASK_TYPE" "$TASK_SUBTYPE")
TOOLS=$(get_allowed_tools)

# Construct claude command
CMD="claude --model $MODEL --allowedTools '$TOOLS' --settings $CONFIG_FILE --add-dir $PROJECT_ROOT $*"

# Execute claude with the specific configuration
echo "Using model: $MODEL for task: $TASK_TYPE/$TASK_SUBTYPE"
eval "$CMD"
