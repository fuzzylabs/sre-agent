#!/bin/bash
# Build and push SRE Agent Docker images to GitHub Container Registry
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="ghcr.io"
REPO_OWNER="fuzzylabs"  # Change this to your GitHub username/org
IMAGE_PREFIX="sre-agent"

# Check if user is logged into GHCR
echo -e "${BLUE}🔍 Checking GitHub Container Registry login...${NC}"
if ! docker login ghcr.io --username dummy --password dummy 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Please log in to GitHub Container Registry first:${NC}"
    echo -e "${BLUE}docker login ghcr.io -u YOUR_GITHUB_USERNAME${NC}"
    echo -e "${BLUE}Use a Personal Access Token with 'write:packages' scope as password${NC}"
    exit 1
fi

# Define images to build
declare -A IMAGES=(
    ["kubernetes"]="sre_agent/servers/mcp-server-kubernetes:sre_agent/servers/mcp-server-kubernetes/Dockerfile"
    ["github"]="sre_agent:sre_agent/servers/github/Dockerfile"
    ["prompt-server"]=".:sre_agent/servers/prompt_server/Dockerfile"
    ["llm-server"]=".:sre_agent/llm/Dockerfile"
    ["orchestrator"]=".:sre_agent/client/Dockerfile"
)

# Build and push each image
for image_name in "${!IMAGES[@]}"; do
    IFS=':' read -r context dockerfile <<< "${IMAGES[$image_name]}"

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
done

echo -e "${GREEN}🎉 All core SRE Agent images built and pushed successfully!${NC}"
echo -e "${BLUE}Images available at:${NC}"
for image_name in "${!IMAGES[@]}"; do
    echo -e "  ${REGISTRY}/${REPO_OWNER}/${IMAGE_PREFIX}-${image_name}:latest"
done
