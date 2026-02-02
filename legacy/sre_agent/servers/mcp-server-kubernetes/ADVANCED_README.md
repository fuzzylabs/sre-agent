# Advanced README for mcp-server-kubernetes

### Non-Destructive Mode

You can run the server in a non-destructive mode that disables all destructive operations (delete pods, delete deployments, delete namespaces, etc.) by setting the `ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS` environment variable to `true`:

```shell
ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS=true npx mcp-server-kubernetes
```

This feature is particularly useful for:

- **Production environments**: Prevent accidental deletion or modification of critical resources
- **Shared clusters**: Allow multiple users to safely explore the cluster without risk of disruption
- **Educational settings**: Provide a safe environment for learning Kubernetes operations
- **Demonstration purposes**: Show cluster state and resources without modification risk

When enabled, the following destructive operations are disabled:

- `delete_pod`: Deleting pods
- `delete_deployment`: Deleting deployments
- `delete_namespace`: Deleting namespaces
- `uninstall_helm_chart`: Uninstalling Helm charts
- `delete_cronjob`: Deleting cronjobs
- `cleanup`: Cleaning up resources

All read-only operations like listing resources, describing pods, getting logs, etc. remain fully functional.

For Non destructive mode in Claude Desktop, you can specify the env var like this:

```json
{
  "mcpServers": {
    "kubernetes-readonly": {
      "command": "npx",
      "args": ["mcp-server-kubernetes"],
      "env": {
        "ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS": "true"
      }
    }
  }
}
```

### SSE Transport

To enable [SSE transport](https://modelcontextprotocol.io/docs/concepts/transports#server-sent-events-sse) for mcp-server-kubernetes, use the ENABLE_UNSAFE_SSE_TRANSPORT environment variable.

```shell
ENABLE_UNSAFE_SSE_TRANSPORT=1 npx flux159/mcp-server-kubernetes
```

This will start an http server with the `/sse` endpoint for server-sent events. Use the `PORT` env var to configure the server port.

```shell
ENABLE_UNSAFE_SSE_TRANSPORT=1 PORT=3001 npx flux159/mcp-server-kubernetes
```

This will allow clients to connect via HTTP to the `/sse` endpoint and receive server-sent events. You can test this by using curl (using port 3001 from above):

```shell
curl http://localhost:3001/sse
```

You will receive a response like this:

```
event: endpoint
data: /messages?sessionId=b74b64fb-7390-40ab-8d16-8ed98322a6e6
```

Take note of the session id and make a request to the endpoint provided:

```shell
curl -X POST -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "id": 1234, "method": "tools/call", "params": {"name": "list_pods", "namespace": "default"}}'  "http://localhost:3001/messages?sessionId=b74b64fb-7390-40ab-8d16-8ed98322a6e6"
```

If there's no error, you will receive an `event: message` response in the localhost:3001/sse session.

Note that normally a client would handle this for you. This is just a demonstration of how to use the SSE transport.

#### Documentation on Running SSE Mode with Docker
Complete Example
Assuming your image name is flux159/mcp-server-kubernetes and you need to map ports and set environment parameters, you can run:

```shell
docker  run --rm -it -p 3001:3001 -e ENABLE_UNSAFE_SSE_TRANSPORT=1  -e PORT=3001   -v ~/.kube/config:/home/appuser/.kube/config   flux159/mcp-server-kubernetes
```
⚠️ Key safety considerations
When deploying SSE mode using Docker, due to the insecure SSE transport protocol and sensitive configuration file mounting, strict security constraints must be implemented in the production environment

mcp config
```shell
{
  "mcpServers": {
    "mcp-server-kubernetes": {
      "url": "http://localhost:3001/sse",
      "args": []
    }
  }
}
```

### Why is SSE Transport Unsafe?

SSE transport exposes an http endpoint that can be accessed by anyone with the URL. This can be a security risk if the server is not properly secured. It is recommended to use a secure proxy server to proxy to the SSE endpoint. In addition, anyone with access to the URL will be able to utilize the authentication of your kubeconfig to make requests to your Kubernetes cluster. You should add logging to your proxy in order to monitor user requests to the SSE endpoint.
