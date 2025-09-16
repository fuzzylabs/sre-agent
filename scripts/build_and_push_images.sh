#!/bin/bash
# Build and push SRE Agent Docker images to GitHub Container Registry
set -e

# Ensure we're using bash
if [ -z "$BASH_VERSION" ]; then
    echo "This script requires bash. Please run with: bash $0"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Update REPO_OWNER to your GitHub username/organization
REGISTRY="ghcr.io"
REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-your-github-username}"  # Set this to your GitHub username/org
IMAGE_PREFIX="sre-agent"

# Check if REPO_OWNER is set
if [ "$REPO_OWNER" = "your-github-username" ]; then
    echo -e "${RED}❌ Please set REPO_OWNER in the script or set GITHUB_REPOSITORY_OWNER environment variable${NC}"
    echo -e "${YELLOW}Example: export GITHUB_REPOSITORY_OWNER=your-username${NC}"
    exit 1
fi

# Check if Docker is running
echo -e "${BLUE}🔍 Checking Docker status...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠️  Make sure you're logged into GitHub Container Registry:${NC}"
echo -e "${BLUE}docker login ghcr.io -u YOUR_GITHUB_USERNAME${NC}"
echo -e "${BLUE}Use a Personal Access Token with 'write:packages' scope as password${NC}"
echo ""

# Function to build and push an image
build_and_push_image() {
    local image_name="$1"
    local context="$2"
    local dockerfile="$3"

    echo -e "${BLUE}🔨 Building ${image_name}...${NC}"

    # Build the image
    docker build \
        -t "${REGISTRY}/${REPO_OWNER}/${IMAGE_PREFIX}-${image_name}:latest" \
        -f "${dockerfile}" \
        "${context}"

    echo -e "${BLUE}📤 Pushing ${image_name} to GHCR...${NC}"

    # Push the image
    docker push "${REGISTRY}/${REPO_OWNER}/${IMAGE_PREFIX}-${image_name}:latest"

    echo -e "${GREEN}✅ Successfully pushed ${image_name}${NC}"
}

# Build and push each core service image
echo -e "${BLUE}🚀 Building and pushing core SRE Agent images...${NC}"

build_and_push_image "kubernetes" "sre_agent/servers/mcp-server-kubernetes" "sre_agent/servers/mcp-server-kubernetes/Dockerfile"
build_and_push_image "github" "sre_agent" "sre_agent/servers/github/Dockerfile"
build_and_push_image "prompt-server" "." "sre_agent/servers/prompt_server/Dockerfile"
build_and_push_image "llm-server" "." "sre_agent/llm/Dockerfile"
build_and_push_image "orchestrator" "." "sre_agent/client/Dockerfile"

echo -e "${GREEN}🎉 All core SRE Agent images built and pushed successfully!${NC}"
echo -e "${BLUE}Images available at:${NC}"
echo -e "  ${REGISTRY}/${REPO_OWNER}/${IMAGE_PREFIX}-kubernetes:latest"
echo -e "  ${REGISTRY}/${REPO_OWNER}/${IMAGE_PREFIX}-github:latest"
echo -e "  ${REGISTRY}/${REPO_OWNER}/${IMAGE_PREFIX}-prompt-server:latest"
echo -e "  ${REGISTRY}/${REPO_OWNER}/${IMAGE_PREFIX}-llm-server:latest"
echo -e "  ${REGISTRY}/${REPO_OWNER}/${IMAGE_PREFIX}-orchestrator:latest"
