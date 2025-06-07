# GAR set-up

> [!WARNING]
> This is intended for development use only. Production images are built and pushed automatically via GitHub action after changes are approved and merged into the main branch.

Instead of accessing Docker images locally, you can retrieve them from GAR (Google Artifact Registry) on GCP. To set this up you will need:

1. GAR enabled in your GCP account
2. A private/public GAR repository for your MCP Servers, for example create a repo named `mcp` either through the UI, CLI, or Terraform. This repo currently stores the following images:

```shell
`mcp/github`
`mcp/kubernetes`
`mcp/slack`
`mcp/sre-orchestrator`
`mcp/prompt-server`
`mcp/llm-server
```

3. Set the following AWS environment variables and ensure you have your AWS credentials set to access the ECR:

```shell
export CLOUDSDK_CORE_PROJECT=<YOUR GCP PROJECT ID>
export CLOUDSDK_COMPUTE_REGION=<YOUR GCP COMPUTE REGION>
```

Then run the `build_push_docker.sh` script to build and push the Docker images for each of the MCP servers:

```shell
bash build_push_docker.sh
```

Once this is done, you can access and pull the images from the following location:

```shell
${CLOUDSDK_COMPUTE_REGION}-docker.pkg.dev/${CLOUDSDK_CORE_PROJECT}/mcp/${name}:latest
```

For example, the Slack MCP server image location could look like:

```shell
europe-west2-docker.pkg.dev/test-project-id/mcp/slack:latest
```
