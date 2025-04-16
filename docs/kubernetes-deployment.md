# Kubernetes Deployment

This page contains the steps to deploy the MCP servers and MCP client onto Kubernetes with an exposed LoadBalancer endpoint.

> [!WARNING]
> This deployment is not yet "production-ready" and uses transports the bearer token through HTTP which is not secure.

## Pre-requisites

This page assumes you have an EKS cluster set-up including:
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

## Environment variables

To avoid committing our AWS account-ID and region, we use a separate package, `envsubst` to substitute variables into the Kubernetes manifests as this is not directly supported.

This package can be installed through `brew` through the `gettext` package as a dependency:

```
brew install gettext
```

If you do not wish to install this package, you can manually change all references to environment variables across the Kubernetes manifests.

The required environment variables needed to be set are:

```
export AWS_ACCOUNT_ID=<YOUR AWS ACCOUNT ID>
export AWS_REGION=<YOUR AWS REGION>
```


## Kubernetes secrets

To enable authentication to Anthropic, Slack and GitHub, and set the bearer token, we use Kubernetes secrets. The following values must be set before deploying any of the services.

SRE-MCP-Client:
- `DEV_BEARER_TOKEN`

Anthropic:
- `ANTHROPIC_API_KEY`

Slack:
- `CHANNEL_ID`
- `SLACK_SIGNING_SECRET`
- `SLACK_BOT_TOKEN`
- `SLACK_TEAM_ID`

GitHub:
- `GITHUB_PERSONAL_ACCESS_TOKEN`

If you have set-up a `.env` file with these values, the secrets can be set through the following command:

```
kubectl create secret generic sre-agent-secrets -n sre-agent --from-env-file=path/to/.env
```

and check this is created with the correct key names:

```
kubectl describe secret/sre-agent-secrets -n sre-agent
```

which should look something like:

```
Name:         sre-agent-secrets
Namespace:    sre-agent
Labels:       <none>
Annotations:  <none>

Type:  Opaque

Data
====
ANTHROPIC_API_KEY:  108 bytes
CHANNEL_ID:         16 bytes
GITHUB_PERSONAL_ACCESS_TOKEN: 94 bytes
SLACK_BOT_TOKEN:    57 bytes
SLACK_TEAM_ID:      9 bytes
SLACK_SIGNING_SECRET:      9 bytes
DEV_BEARER_TOKEN:      9 bytes
```

## Kubernetes manifests

Once all environment variables and Kubernetes secrets have been set, you can apply the Kubernetes manifests to deploy the MCP servers and expose the MCP-client endpoint.

Authenticate with the MCP cluster:

```
aws eks update-kubeconfig --region $AWS_REGION --name $MCP_CLUSTER_NAME
```

We provide a bash script that runs the `kubectl apply` command for the manifests and this depends on the `envsubst` package to update the environment variables:

```
bash k8s/apply_manifests.sh
```

This deploys all pods and services to the `sre-agent` namespace. Check that the pods and services all deploy correctly without erroring or restarting with the following command:
```
kubectl get pods -n sre-agent
kubectl get svc -n sre-agent
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
http://<EXTERNAL-IP>/diagnose?service=<service> \
-H 'accept: application/json' \
-H 'Authorization: Bearer <token>'
```
