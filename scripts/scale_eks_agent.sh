#!/bin/bash

CLUSTER_NAME="sre-agent"
NODEGROUP_NAME="main"

if [ "$1" == "--down" ]; then
  echo "Scaling node group '$NODEGROUP_NAME' down to 0..."
  aws eks update-nodegroup-config \
    --cluster-name "$CLUSTER_NAME" \
    --nodegroup-name "$NODEGROUP_NAME" \
    --scaling-config minSize=0,maxSize=1,desiredSize=0
elif [ "$1" == "--up" ]; then
  echo "Scaling node group '$NODEGROUP_NAME' up to 1..."
  aws eks update-nodegroup-config \
    --cluster-name "$CLUSTER_NAME" \
    --nodegroup-name "$NODEGROUP_NAME" \
    --scaling-config minSize=0,maxSize=1,desiredSize=1
else
  echo "Usage: $0 [--up | --down]"
  exit 1
fi
