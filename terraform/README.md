# SRE Agent Terraform Configuration

> [!WARNING]
> This Terraform configuration is not production-ready. It provides the bare minimum infrastructure required to deploy the SRE Agent as a proof of concept. For production deployments, additional security considerations, high availability configurations, and proper secrets management should be implemented.

> [!NOTE]
> This configuration assumes that the target EKS cluster is already created, and is in the same AWS account as the SRE Agent.

This directory contains Terraform configuration to deploy the infrastructure for the SRE agent to AWS.

## Infrastructure Components

The Terraform configuration deploys the following AWS resources:

- **Amazon VPC** with public and private subnets
- **Amazon EKS cluster** for running the SRE agent
- **Amazon ECR** repositories for Docker images
- **Elastic Load Balancer (ELB)** for external access to services
- **IAM roles and policies** for cross-cluster access
- **S3 bucket** for ELB access logs
- **EKS Access Policy** allowing cluster admin access to specified IAM principal
- **S3 bucket and DynamoDB table** for Terraform state management

The configuration references an existing target EKS cluster that will be monitored by the SRE agent.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform (version == 1.5.5)
- kubectl
- Docker (for building and pushing images)
- Existing target EKS cluster for monitoring

## Setting Up Remote State Storage

The Terraform configuration uses an S3 bucket and DynamoDB table for remote state storage. To set this up:

1. **Initial Setup**
   - Comment out the `backend "s3"` block in `backend.tf`
   - This allows Terraform to create the S3 bucket and DynamoDB table

2. **Create State Storage Resources**
   ```bash
   terraform init
   terraform apply
   ```
   This will create the S3 bucket and DynamoDB table for state storage.

3. **Migrate State to Remote Storage**
   - Uncomment the `backend "s3"` block in `backend.tf`
   - Run `terraform init` again
   - When prompted, confirm that you want to migrate the state to the new backend

4. **Verify State Migration**
   - Run `terraform plan` to ensure everything is working correctly
   - The state should now be stored in the S3 bucket

## Getting Started

1. **Copy and customise the terraform.tfvars file**

   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your specific values
   ```

   Be sure to replace the `aws_account_id`, `cluster_admin_principal_arn`, and `target_cluster_name` with your actual AWS account ID, IAM principal ARN, and target EKS cluster name.

2. **Initialize Terraform**

   ```bash
   terraform init
   ```

3. **Plan the deployment**

   ```bash
   terraform plan
   ```

4. **Apply the configuration**

   ```bash
   terraform apply
   ```

5. **Configure kubectl to access the EKS cluster**

   ```bash
   aws eks update-kubeconfig --region $(terraform output -raw aws_region) --name $(terraform output -raw eks_cluster_name)
   ```

6. **Build and push Docker images**

   From the project root directory:

   ```bash
   export AWS_ACCOUNT_ID=$(terraform output -raw aws_account_id)
   export AWS_REGION=$(terraform output -raw aws_region)
   bash build_push_docker.sh
   ```

7. **Deploy Kubernetes resources separately**

   Kubernetes resources including namespaces, deployments, services, and MCP servers are deployed separately and not managed by this Terraform configuration.

   See the [Kubernetes Deployment](../docs/kubernetes-deployment.md) documentation for details on how to deploy the Kubernetes resources.

## Clean Up

To destroy all resources created by Terraform:

```bash
terraform destroy
```

## Notes

- All Kubernetes resources (namespaces, deployments, services) are deployed separately from this Terraform configuration.
- This configuration references an existing target EKS cluster instead of creating a new one.
- The EKS clusters are set up with public endpoints for ease of access. For production deployments, consider securing these endpoints.
- The IAM roles and policies are set up for demo purposes. Review and adjust them according to your security requirements before deploying to production.
- The ELB is configured with HTTP and TCP listeners. For production environments, consider using HTTPS with an SSL certificate.
- The `cluster_admin_principal_arn` variable must be set to grant administrative access to the EKS cluster. This can be an IAM user or role ARN that requires access to manage the cluster.
