# ECR set-up

Instead of accessing Docker images locally, you can retrieve them from ECR (Elastic Container Registry) on AWS. To set this up you will need:

1. An ECR in your AWS account
2. Private/public ECR repositories for each MCP Server, for example, for a `github` MCP server create a repo named `mcp/github` either through the UI, CLI, or Terraform. This repo currently requires:
```
`mcp/github`
`mcp/kubernetes`
`mcp/slack`
`mcp/sre-orchestrator`
```
3. Set the following AWS environment variables and ensure you have your AWS credentials set to access the ECR:

```
export AWS_ACCOUNT_ID=<YOUR AWS ACCOUNT ID>
export AWS_REGION=<region>
```

Then run the `build_push_docker.sh` script to build and push the Docker images for each of the MCP servers:
```
bash build_push_docker.sh
```

Once this is done, you can access and pull the images from the following location:
```
${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mcp/${mcp_server_name}:latest
```
For example, the Slack MCP server image location could look like:
```
12345678.dkr.ecr.eu-west-2.amazonaws.com/mcp/slack:latest
```
