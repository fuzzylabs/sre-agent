#!/bin/bash

# Configure AWS EKS Kubeconfig
aws eks update-kubeconfig --region eu-west-2 --name no-loafers-for-you

# Start the Node.js application
exec node dist/index.js
