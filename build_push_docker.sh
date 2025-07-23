#!/bin/bash
set -euo pipefail

# Source .env if it exists (optional for some targets)
if [[ -f .env ]]; then
  source .env
fi

usage()
{
    echo "usage: <command> <--aws|--gcp|--ghcr|--dockerhub|--local>"
    echo ""
    echo "Registry Options:"
    echo "  --aws        Push to AWS ECR (requires AWS_ACCOUNT_ID, AWS_REGION in .env)"
    echo "  --gcp        Push to GCP GAR (requires CLOUDSDK_* vars in .env)"
    echo "  --ghcr       Push to GitHub Container Registry (requires GITHUB_TOKEN)"
    echo "  --dockerhub  Push to Docker Hub (requires DOCKER_USERNAME, DOCKER_TOKEN)"
    echo "  --local      Build locally only, no push"
}

if [[ $@ == "" ]]; then
  echo "No arguments were passed"
  usage
  exit 1
fi

REGISTRY_TARGET=""
for arg in "$@"; do
  shift
  case "$arg" in
    '--aws')       REGISTRY_TARGET="AWS" ;;
    '--gcp')       REGISTRY_TARGET="GCP" ;;
    '--ghcr')      REGISTRY_TARGET="GHCR" ;;
    '--dockerhub') REGISTRY_TARGET="DOCKERHUB" ;;
    '--local')     REGISTRY_TARGET="LOCAL" ;;
    *)             REGISTRY_TARGET="UNKNOWN" ;;
  esac
done

# Authentication and setup based on registry target
if [[ $REGISTRY_TARGET == "AWS" ]]; then
  : "${AWS_ACCOUNT_ID:?Environment variable AWS_ACCOUNT_ID not set}"
  : "${AWS_REGION:?Environment variable AWS_REGION not set}"

  echo "Target: AWS ECR"
  echo "Account ID: $AWS_ACCOUNT_ID"
  echo "Region: $AWS_REGION"

  echo "Authenticating with ECR..."
  aws ecr get-login-password --region "$AWS_REGION" | \
      docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

elif [[ $REGISTRY_TARGET == "GCP" ]]; then
  : "${CLOUDSDK_CORE_PROJECT:?Environment variable CLOUDSDK_CORE_PROJECT not set}"
  : "${CLOUDSDK_COMPUTE_REGION:?Environment variable CLOUDSDK_COMPUTE_REGION not set}"

  echo "Target: GCP GAR"
  echo "Project ID: $CLOUDSDK_CORE_PROJECT"
  echo "Region: $CLOUDSDK_COMPUTE_REGION"

  echo "Authenticating with GAR..."
  gcloud auth configure-docker "${CLOUDSDK_COMPUTE_REGION}-docker.pkg.dev" --quiet

elif [[ $REGISTRY_TARGET == "GHCR" ]]; then
  : "${GITHUB_TOKEN:?Environment variable GITHUB_TOKEN not set. Get one at https://github.com/settings/tokens}"

  echo "Target: GitHub Container Registry (GHCR)"
  echo "Repository: ghcr.io/fuzzylabs/sre-agent-*"

  echo "Authenticating with GHCR..."
  echo "$GITHUB_TOKEN" | docker login ghcr.io --username "$(gh api user --jq .login)" --password-stdin

elif [[ $REGISTRY_TARGET == "DOCKERHUB" ]]; then
  : "${DOCKER_USERNAME:?Environment variable DOCKER_USERNAME not set}"
  : "${DOCKER_TOKEN:?Environment variable DOCKER_TOKEN not set}"

  echo "Target: Docker Hub"
  echo "Username: $DOCKER_USERNAME"

  echo "Authenticating with Docker Hub..."
  echo "$DOCKER_TOKEN" | docker login --username "$DOCKER_USERNAME" --password-stdin

elif [[ $REGISTRY_TARGET == "LOCAL" ]]; then
  echo "Target: Local build only (no push)"

else
  echo "Unknown registry target: $REGISTRY_TARGET"
  usage
  exit 1
fi

build_and_push() {
    local name=$1
    local dockerfile=$2
    local context=$3

    echo "Building ${name} service..."
    docker build -t sre-agent/${name}:latest -f ${dockerfile} ${context} --platform linux/amd64

    # Determine image tag based on registry target
    local image_tag=""
    case $REGISTRY_TARGET in
        "AWS")
            image_tag="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mcp/${name}:latest"
            ;;
        "GCP")
            image_tag="${CLOUDSDK_COMPUTE_REGION}-docker.pkg.dev/${CLOUDSDK_CORE_PROJECT}/mcp/${name}:dev"
            ;;
        "GHCR")
            image_tag="ghcr.io/fuzzylabs/sre-agent-${name}:latest"
            ;;
        "DOCKERHUB")
            image_tag="fuzzylabs/sre-agent-${name}:latest"
            ;;
        "LOCAL")
            echo "✅ Built ${name} locally (tagged as sre-agent/${name}:latest)"
            return 0
            ;;
    esac

    # Tag and push to registry
    docker tag sre-agent/${name}:latest "${image_tag}"
    echo "Pushing ${name} to ${REGISTRY_TARGET}..."
    docker push "${image_tag}"
    echo "✅ Pushed ${image_tag}"
}

# Build and push all services
echo "🚀 Starting build and push process for all SRE Agent services..."

build_and_push "github" "sre_agent/servers/github/Dockerfile" "sre_agent/"
build_and_push "kubernetes" "sre_agent/servers/mcp-server-kubernetes/Dockerfile" "sre_agent/servers/mcp-server-kubernetes"
build_and_push "slack" "sre_agent/servers/slack/Dockerfile" "sre_agent/"
build_and_push "orchestrator" "sre_agent/client/Dockerfile" "."
build_and_push "llm-server" "sre_agent/llm/Dockerfile" "."
build_and_push "prompt-server" "sre_agent/servers/prompt_server/Dockerfile" "."
build_and_push "llama-firewall" "sre_agent/firewall/Dockerfile" "."

echo ""
echo "🎉 All services built and pushed successfully!"
if [[ $REGISTRY_TARGET != "LOCAL" ]]; then
    echo "📋 Images available at:"
    case $REGISTRY_TARGET in
        "AWS")
            echo "   ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mcp/*:latest"
            ;;
        "GCP")
            echo "   ${CLOUDSDK_COMPUTE_REGION}-docker.pkg.dev/${CLOUDSDK_CORE_PROJECT}/mcp/*:dev"
            ;;
        "GHCR")
            echo "   ghcr.io/fuzzylabs/sre-agent-*:latest"
            ;;
        "DOCKERHUB")
            echo "   fuzzylabs/sre-agent-*:latest"
            ;;
    esac
else
    echo "📋 Local images tagged as: sre-agent/*:latest"
fi
