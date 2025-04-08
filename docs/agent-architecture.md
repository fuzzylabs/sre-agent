# Agent Architecture

The following diagram represents the overall architecture of the SRE agent. It consists of four MCP servers that communicate with an LLM via an MCP client. The agent is triggered by Slack bot which sends a request to prompt the LLM via the MCP client.

![agent-architecture](imgs/agent-architecture.png)

MCP Servers:

- **AWS MCP Server**: This server is responsible for interacting with AWS services to retrieve information about the error and deployed services to diagnose an issue.
- **K8s MCP Server**: This server is responsible for interacting with a K8s cluster directly to retrieve information about the error from the logs.
- **Github MCP Server**: This server is responsible for interacting with the codebase in GitHub to identify the root cause of any application errors.
- **Slack MCP Server**: This server is responsible for sending a message back to the `site-reliability` channel in Slack.

## Production Journey

We aim to scale up the agent from a local deployment to a production deployment. The following steps outline the journey:

1. Initially, we deploy the agent locally using the Claude Desktop to orchestrate the whole process.
2. Once we have an initial PoC in Claude Desktop we deploy a client and the servers using API calls to Anthropic for our LLM.
3. Finally, we deploy our own model swapping out Anthropic for calls to our own service.

## Individual Server-Client Architectures

### AWS MCP Server

TBC

### K8s MCP Server

TBC

### Github MCP Server

TBC

### Slack MCP Server

![slack-server-client-architecture](imgs/slack-server-client-architecture.png)

Once the agent has been able to diagnose the root cause of the error using the AWS, K8s, and GitHub MCP servers it will use the Slack MCP server to package up the error diagnsosis and post it back to the `site-reliability` channel. In the event that the agent is unable to diagnose the issue, the Slack MCP server will send a message back to the `site-reliability` channel with the error message.
