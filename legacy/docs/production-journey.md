# Production Journey

Our aim is to scale up the agent from a local deployment to a production deployment. The following steps outline the journey:

1. Firstly, we will deploy the agent locally using a AI application, like Claude Desktop or Cursor, to orchestrate the whole process.

https://github.com/user-attachments/assets/b1b7199b-091a-404c-b867-99560c15b7f1

2. Once we have an initial PoC using an AI app as our client we will remove these training wheels and deploy a local implementation of the client and the servers with Docker Compose using API calls to Anthropic for our LLM.

https://github.com/user-attachments/assets/ec5736ad-c483-4693-93f2-742a84abfc76

3. Once we have deployed the agent locally using Docker Compose we will deploy the agent to a Kubernetes cluster in AWS.

https://github.com/user-attachments/assets/df43c212-7709-48c4-9d9d-b2329a82910e

4. Finally, we will deploy our own model swapping out Anthropic for calls to our own service.

Demo: TBC
