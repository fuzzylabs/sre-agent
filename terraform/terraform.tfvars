# AWS settings
aws_region    = "eu-west-2"  # London region
aws_account_id = "554043692091"  # Replace with your AWS account ID

# Name prefix for all resources
name_prefix = "sre-agent"

# Existing target cluster settings
target_cluster_name = "no-loafers-for-you"
target_cluster_role_arn = "arn:aws:iam::554043692091:role/NoLoafersClusterRole"
target_cluster_arn = "arn:aws:eks:eu-west-2:554043692091:cluster/no-loafers-for-you"

# EKS cluster access
cluster_endpoint_public_access  = true
cluster_endpoint_private_access = true

# ECR repositories
ecr_repositories = [
  "mcp/github",
  "mcp/kubernetes",
  "mcp/slack",
  "mcp/sre-orchestrator"
]

# EKS managed node groups
eks_managed_node_groups = {
  main = {
    use_name_prefix = false
    min_size      = 1
    max_size      = 2
    desired_size  = 1
    instance_types = ["t3.medium"]
  }
}

cluster_admin_principal_arn = "arn:aws:iam::554043692091:role/aws-reserved/sso.amazonaws.com/eu-west-2/AWSReservedSSO_AdministratorAccess_f33dabca8da94838"
