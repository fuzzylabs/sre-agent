#!/bin/bash
set -euo pipefail
source .env

echo "🔑 Setting up GCP credentials..."

# Run gcloud auth login command
echo "Running gcloud auth login"
gcloud auth login

# Determine the authenticated user
echo "Authenticated as:"
gcloud auth list --format="value(account)"

# Get the GKE cluster credentials
echo "Getting cluster credentials..."
gcloud container clusters get-credentials ${TARGET_GKE_CLUSTER_NAME} --region ${CLOUDSDK_COMPUTE_REGION} --project ${CLOUDSDK_CORE_PROJECT}

# Determine the cluster info
echo "Cluster details:"
kubectl cluster-info

# Done
echo "✅ GCP credentials have been successfully configured!"
