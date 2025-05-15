# Kubernetes Deployment

This page contains the steps to deploy the MCP servers and MCP client onto Kubernetes with an exposed LoadBalancer endpoint.

> [!WARNING]
> This deployment is not yet "production-ready" and transports the bearer token through HTTP which is not secure.

## Pre-requisites

The following tools are needed for deploying to Kubernetes and debugging:
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [helm](https://helm.sh/docs/intro/install/)

This page also assumes you have an EKS cluster set-up including:
- The required VPC with both private and public subnets,
- Associated access roles
-  At least one node group deployed
   -  `t3.medium` EC2 instance type
   -  We have tested this with
   -  Desired size: 1 node
   -  Minimum size: 1 node
   -  Maximum size: 2 nodes
   -  This is priced at roughly `$0.0472` an hour with On Demand pricing
-  The following EKS add-ons:
   - CoreDNS
   - External DNS
   - Amazon VPC CNI
   - kube-proxy

You can use the Terraform configuration to deploy the EKS cluster with the required add-ons and set-up the IAM roles and policies. See the [Terraform README](/terraform/README.md) for more details.

> [!NOTE]
> The provided Terraform configuration is not production-ready and provides only the bare minimum infrastructure required for a proof of concept deployment. For production use, additional security hardening, high availability configurations, and proper secrets management should be implemented.

## Kubernetes deployment

You can deploy the agent to a Kubernetes cluster through the Helm chart provided. First, you need to authenticate with the MCP cluster:

```
aws eks update-kubeconfig --region $AWS_REGION --name $MCP_CLUSTER_NAME
```

If you created the cluster with Terraform, the MCP access role name is set in the Terraform outputs. You can retrieve it with the following command:

```
cd terraform
export MCP_ACCESS_ROLE_NAME=$(terraform output -raw mcp_access_role_name)
cd ..
```

Before deploying the Helm chart, you need to create a `values-secrets.yaml` file, we have provided a [`values-secrets.yaml.example`](../charts/sre-agent/values-secrets.yaml.example) file. We have also provided a helper function for creating this which can be run with the following command:

```bash
python credential_setup.py --helm
```

Now we can deploy the Helm chart with the `install` command:

```
helm install sre-agent charts/sre-agent -f charts/sre-agent/values-secrets.yaml
```

> [!NOTE]
> You can perform a "dry-run" of the Helm chart to check for any errors before deploying with the following command:
> ```
> helm install sre-agent charts/sre-agent -f charts/sre-agent/values-secrets.yaml --dry-run
> ```

The `helm install` deploys all pods and services to the `sre-agent` namespace by default. Check that the pods and services all deploy correctly without erroring or restarting with the following command:
```
kubectl get pods -n sre-agent
kubectl get svc -n sre-agent
```

## Toggling servers

As we increase the number of supported servers there is the possibility that you may not require all of the provided MCP servers, to turn on or off their deployments there is a value in the Helm [`values.yaml` file](/charts/sre-agent/values.yaml) for each of the MCP servers, taking the Slack MCP server for example:

```
mcpSlack:
  enabled: true
```

can be disabled by changing it to:

```
mcpSlack:
  enabled: false
```

If you have already deployed a service but no longer wish to use it, update the respective `enabled` value then run the Helm upgrade command:

```
helm upgrade sre-agent charts/sre-agent
```

## AWS permissions

> [!NOTE]
> In this section we reference Kubernetes in multiple contexts, the first being the Kubernetes cluster we are deploying the MCP "agent" (MCP CLUSTER) to and the second being the target cluster we wish to debug with the agent (TARGET CLUSTER).
> We also assume that the MCP CLUSTER and the TARGET CLUSTER exist on the same AWS account. In practice, this may not be the case.
> Future work is planned to perform the actions in this section through Terraform for a more robust deployment.

To enable the Kubernetes MCP service on the MCP CLUSTER to authenticate with the TARGET CLUSTER and have Read-Only access to the cluster without having to manually update AWS credentials on the pod, we require the Kubernetes MCP service to assume an AWS role through OIDC.

Through the TARGET CLUSTER we give permission to the MCP CLUSTER role with Read-Only access.

On the start-up of the `mcp/kubernetes` pod, it runs the script [mcp-server-kubernetes/startup.sh](/sre_agent/servers/mcp-server-kubernetes/startup.sh) which includes the following call to set-up the Kubernetes context:

```
aws eks update-kubeconfig --region $AWS_REGION --name $TARGET_EKS_CLUSTER_NAME
```

### Creating the role

Through the IAM on your AWS account create a role with the name `MCP-access-role`.

The role name has the following ARN:
```
arn:aws:iam::${AWS_ACCOUNT_ID}:role/MCP-access-role
```

Add the Trust relationship (make sure to update the missing values in <>):

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::<YOUR AWS ACCOUNT ID>:oidc-provider/oidc.eks.<AWS REGION>.amazonaws.com/id/<MCP CLUSTER OIDC ID>"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "oidc.eks.<AWS REGION>.amazonaws.com/id/<MCP CLUSTER OIDC ID>:sub": "system:serviceaccount:sre-agent:mcp-kubernetes-sa",
                    "oidc.eks.<AWS REGION>.amazonaws.com/id/<MCP CLUSTER OIDC ID>:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

If the MCP CLUSTER and the TARGET CLUSTER are in different AWS accounts, this IAM role should be created in the same account as the TARGET CLUSTER.

### Assigning permissions

Once we have attached the role to the MCP CLUSTER OIDC, we can then give permission from the TARGET CLUSTER to the role for Read-Only Access (`eks:DescribeCluster` action).

On the `MCP-access-role` IAM role create a permission policy under `Permissions/Permissions policies`:
```
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": "eks:DescribeCluster",
			"Resource": "arn:aws:eks:eu-west-2:<TARGET AWS ACCOUNT ID>:cluster/<TARGET CLUSTER NAME>"
		}
	]
}
```

## Finding your endpoint

Once permissions have been granted and pods deployed you will be able to access the MCP client through an IP assigned to the `sre-orchestrator-service`, run:

```
kubectl get svc -n sre-agent
```
and find the IP under EXTERNAL-IP.

> [!WARNING]
> As noted before this deployment is not yet "production-ready" and uses HTTP to transport the bearer token which is not secure. The external IP will also change if you re-deploy the service or the service crashes and restarts.
> In the future, this will be routed to a fixed IP load balancer with HTTPS Nginx ingress.
> If you do not want to expose an IP, feel free to remove the corresponding lines from `k8s/sre-orchestrator.yaml` and port-forward through Kubernetes to access the pod instead.

Then post your request to the diagnose endpoint on the SRE client service containing the bearer token to authorise the request:

```
curl -X POST http://<EXTERNAL-IP>/diagnose \
-H 'accept: application/json' \
-H 'Authorization: Bearer <token>'
-d "text=<service>"
```
