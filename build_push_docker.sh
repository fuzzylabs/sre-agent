#!/bin/bash
set -euo pipefail
source .env

: "${AWS_ACCOUNT_ID:?Environment variable AWS_ACCOUNT_ID not set}"
: "${AWS_REGION:?Environment variable AWS_REGION not set}"

echo "Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"

echo "Authenticating with ECR."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

build_and_push() {
    local name=$1
    local dockerfile=$2
    local context=$3

    echo "Building ${name} MCP Server."
    docker build -t mcp/${name} -f ${dockerfile} ${context} --platform linux/amd64

    local image_tag="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mcp/${name}:dev"
    docker tag mcp/${name}:latest "${image_tag}"

    echo "Pushing ${name} MCP Server to ECR."
    docker push "${image_tag}"
}

build_and_push "github" "sre_agent/servers/github/Dockerfile" "sre_agent/"
build_and_push "kubernetes" "sre_agent/servers/mcp-server-kubernetes/Dockerfile" "sre_agent/servers/mcp-server-kubernetes"
build_and_push "slack" "sre_agent/servers/slack/Dockerfile" "sre_agent/"
build_and_push "sre-orchestrator" "sre_agent/client/Dockerfile" "."
build_and_push "llm-server" "sre_agent/llm/Dockerfile" "."
build_and_push "prompt-server" "sre_agent/servers/prompt_server/Dockerfile" "."
build_and_push "llama-firewall" "sre_agent/servers/llama-firewall/Dockerfile" "."
