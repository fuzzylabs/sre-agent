# Production Journey

We aim to scale up the agent from a local deployment to a production deployment. The following steps outline the journey:

1. Initially, we deploy the agent locally using the Claude Desktop to orchestrate the whole process.

Demo: TBC

2. Once we have an initial PoC in Claude Desktop we remove the Claude desktop training wheels and deploy a local implementation of the client and the servers with Docker Compose using API calls to Anthropic for our LLM.

Demo: TBC

3. Once we have deployed the agent locally using Docker Compose we will deploy the agent to a K8s cluster in AWS.

Demo: TBC

4. Finally, we will deploy our own model swapping out Anthropic for calls to our own service.

Demo: TBC
