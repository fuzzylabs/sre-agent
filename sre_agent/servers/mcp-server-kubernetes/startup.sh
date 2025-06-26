#!/usr/bin/env bash
set -euo pipefail

function log_error_and_exit {
  echo "❌ Failed to update kubeconfig:"
  echo "$1"
  exit 1
}

if [[ -v AWS_REGION ]]; then
  echo "🔧 Updating kubeconfig for EKS cluster..."
  if ! output=$(aws eks update-kubeconfig --region $AWS_REGION --name $TARGET_EKS_CLUSTER_NAME 2>&1); then
    log_error_and_exit "$output"
  fi
elif [[ -v CLOUDSDK_COMPUTE_REGION ]]; then
  echo "🔧 Updating kubeconfig for GKE cluster..."
  if ! output=$(gcloud container clusters get-credentials $TARGET_GKE_CLUSTER_NAME --region $CLOUDSDK_COMPUTE_REGION --project $CLOUDSDK_CORE_PROJECT 2>&1); then
    log_error_and_exit "$output"
  fi
else
  echo "❌ No supported environment variables not found"
  exit 1
fi

echo "✅ Kubeconfig updated successfully."
echo "🚀 Starting Node.js application..."
exec node dist/index.js
