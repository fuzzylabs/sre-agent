# 1. Ensure environment variables are exported from your .env file
#    (Make sure you are in the directory containing .env or provide the full path)
export $(grep -v '^#' .env | xargs)

cat k8s/namespace.yaml \
    k8s/agent.yaml \
    k8s/mcp-kubernetes.yaml \
    k8s/mcp-slack.yaml \
    k8s/mcp-github.yaml | \
    envsubst '${AWS_ACCOUNT_ID} ${AWS_REGION} ${MCP_KUBERNETES_ROLE_NAME}' | \
    kubectl apply -f -

# 3. Optional: Unset the exported variables from the environment if you want cleanup
unset $(grep -v '^#' .env | sed -E 's/=.*//' | xargs)
