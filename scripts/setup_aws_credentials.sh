#!/bin/bash

# Create AWS credentials directory if it doesn't exist
mkdir -p ~/.aws

echo "🔑 Setting up AWS credentials..."

# Prompt for AWS credentials
echo "Please paste your AWS credentials block (press Ctrl+D when done):"
credentials=$(cat)

# Extract the credentials using awk
access_key=$(echo "$credentials" | awk '/aws_access_key_id/{print $2}')
secret_key=$(echo "$credentials" | awk '/aws_secret_access_key/{print $2}')
session_token=$(echo "$credentials" | awk '/aws_session_token/{print $2}')

# Create or update the credentials file
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id=$access_key
aws_secret_access_key=$secret_key
aws_session_token=$session_token
EOF

echo "✅ AWS credentials have been successfully configured!"
