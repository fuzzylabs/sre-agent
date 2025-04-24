#!/bin/bash
set -euo pipefail

function log_error_and_exit {
  echo "❌ Failed to update kubeconfig:"
  echo "$1"
  exit 1
}

echo "🔧 Updating kubeconfig for EKS cluster..."
if ! output=$(aws eks update-kubeconfig --region $AWS_REGION --name $TARGET_EKS_CLUSTER_NAME 2>&1); then
  log_error_and_exit "$output"
fi

echo "✅ Kubeconfig updated successfully."
echo "🚀 Starting Node.js application..."
exec node dist/index.js
