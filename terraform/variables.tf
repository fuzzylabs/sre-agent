variable "name_prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "sre-agent"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-west-2"  # London region as referenced in docs
}

variable "vpc_name" {
  description = "Name for the VPC"
  type        = string
  default     = null
}

variable "cluster_name" {
  description = "Name for the EKS cluster"
  type        = string
  default     = null
}

variable "target_cluster_name" {
  description = "Name of the existing target EKS cluster to be monitored"
  type        = string
}

variable "target_cluster_role_arn" {
  description = "IAM role ARN of the existing target EKS cluster"
  type        = string
}

variable "target_cluster_arn" {
  description = "ARN of the existing target EKS cluster"
  type        = string
}

variable "ecr_repositories" {
  description = "List of ECR repositories to create"
  type        = list(string)
  default     = ["mcp/github", "mcp/kubernetes", "mcp/slack", "mcp/sre-orchestrator", "mcp/prompt-server", "mcp/llm-server"]
}

variable "cluster_endpoint_public_access" {
  description = "Whether the EKS cluster endpoint is publicly accessible"
  type        = bool
  default     = true
}

variable "cluster_endpoint_private_access" {
  description = "Whether the EKS cluster endpoint is privately accessible"
  type        = bool
  default     = true
}

variable "eks_managed_node_groups" {
  description = "Map of EKS managed node group definitions"
  type        = map(any)
  default     = {
    main = {
      name         = null  # Will be set via locals
      min_size     = 1
      max_size     = 2
      desired_size = 1
      instance_types = ["t3.medium"]
    }
  }
}

# We assume that the SRE Agent is deployed in the same AWS account as the target EKS cluster
variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
  # No default - must be provided
}

variable "cluster_admin_principal_arn" {
  description = "IAM principal ARN to provide admin access to the EKS cluster"
  type        = string
}

locals {
  vpc_name     = coalesce(var.vpc_name, "${var.name_prefix}-deployment-vpc")
  cluster_name = coalesce(var.cluster_name, var.name_prefix)

  # Set node group name based on name_prefix if not specified
  eks_managed_node_groups = {
    for key, group in var.eks_managed_node_groups : key => merge(group, {
      name = "${var.name_prefix}-${key}-ng"
    })
  }
}
