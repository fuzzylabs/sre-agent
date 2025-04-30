# VPC outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_public_subnets" {
  description = "The IDs of the VPC public subnets"
  value       = module.vpc.public_subnets
}

output "vpc_private_subnets" {
  description = "The IDs of the VPC private subnets"
  value       = module.vpc.private_subnets
}

# EKS outputs
output "eks_cluster_name" {
  description = "The name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "The endpoint for the EKS Kubernetes API"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "eks_oidc_provider" {
  description = "The OIDC provider URL for the EKS cluster"
  value       = module.eks.oidc_provider
}

# Target EKS outputs (existing cluster)
output "target_eks_cluster_name" {
  description = "The name of the existing target EKS cluster"
  value       = var.target_cluster_name
}

output "target_eks_cluster_role_arn" {
  description = "The IAM role ARN of the existing target EKS cluster"
  value       = var.target_cluster_role_arn
}

# ECR outputs
output "ecr_repository_urls" {
  description = "The URLs of the ECR repositories"
  value       = { for repo in var.ecr_repositories : repo => "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${repo}" }
}

output "mcp_access_role_name" {
  description = "The name of the MCP access role"
  value       = aws_iam_role.mcp_access_role.name
}
