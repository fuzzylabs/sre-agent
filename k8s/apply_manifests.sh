#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Determine the directory where the script resides
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# List of manifest files to apply (relative to the script's directory)
MANIFEST_FILES=(
  "namespace.yaml"
  "sre-orchestrator.yaml"
  "mcp-kubernetes.yaml"
  "mcp-github.yaml"
  "mcp-slack.yaml"
  "mcp-prompt-server.yaml"
)


if [ -z "$AWS_ACCOUNT_ID" ]; then
  echo "Error: AWS_ACCOUNT_ID environment variable is not set."
  exit 1
fi

if [ -z "$AWS_REGION" ]; then
  echo "Error: AWS_REGION environment variable is not set."
  exit 1
fi

# Apply the specified Kubernetes manifests
echo "Applying manifests from $SCRIPT_DIR..."
for file in "${MANIFEST_FILES[@]}"; do
  manifest_path="$SCRIPT_DIR/$file"

  if [ -f "$manifest_path" ]; then
    echo "Applying $manifest_path..."
    # Use envsubst to replace environment variables and pipe to kubectl
    # envsubst reads from stdin, so redirect the file content
    envsubst < "$manifest_path" | kubectl apply -f -
    if [ $? -ne 0 ]; then
      echo "Error applying $manifest_path. Aborting."
      exit 1
    fi
  else
    echo "Error: Manifest file '$manifest_path' not found. Aborting."
    exit 1
  fi
done

echo "All specified manifests applied successfully."

exit 0
