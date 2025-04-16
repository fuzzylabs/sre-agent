#!/bin/bash

# Configure AWS EKS Kubeconfig
aws eks update-kubeconfig --region $AWS_REGION --name $TARGET_EKS_CLUSTER_NAME

# Start the Node.js application
exec node dist/index.js
