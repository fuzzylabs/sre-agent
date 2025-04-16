# Production Journey

We aim to scale up the agent from a local deployment to a production deployment. The following steps outline the journey:

1. Initially, we deploy the agent locally using the Claude Desktop to orchestrate the whole process.

https://github.com/user-attachments/assets/b1b7199b-091a-404c-b867-99560c15b7f1

2. Once we have an initial PoC in Claude Desktop we remove the Claude desktop training wheels and deploy a local implementation of the client and the servers with Docker Compose using API calls to Anthropic for our LLM.

https://github.com/user-attachments/assets/804bdc5a-303c-40aa-9f82-74a9d1d40535

3. Once we have deployed the agent locally using Docker Compose we will deploy the agent to a K8s cluster in AWS.

Demo: TBC

4. Finally, we will deploy our own model swapping out Anthropic for calls to our own service.

Demo: TBC
