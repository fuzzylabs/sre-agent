# Create the MCP-access-role
resource "aws_iam_role" "mcp_access_role" {
  name = "${local.cluster_name}-MCP-access-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${var.aws_account_id}:oidc-provider/${module.eks.oidc_provider}"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${module.eks.oidc_provider}:sub" = "system:serviceaccount:sre-agent:mcp-kubernetes-sa",
            "${module.eks.oidc_provider}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${local.cluster_name}-MCP-access-role"
  }
}

# Create policy for the MCP-access-role to access the target EKS cluster
resource "aws_iam_policy" "mcp_access_policy" {
  name        = "${local.cluster_name}-mcp-access-policy"
  description = "Policy for ${local.cluster_name}-MCP-access-role to access the target EKS cluster"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "eks:DescribeCluster"
        Resource = var.target_cluster_arn
      }
    ]
  })
}

# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "mcp_access_policy_attachment" {
  role       = aws_iam_role.mcp_access_role.name
  policy_arn = aws_iam_policy.mcp_access_policy.arn
}

# Access entry for the target cluster
resource "aws_eks_access_entry" "target_cluster_mcp_access" {
  cluster_name  = var.target_cluster_name
  principal_arn = aws_iam_role.mcp_access_role.arn
  user_name     = "${aws_iam_role.mcp_access_role.arn}/{{SessionName}}"
}

# Associate AmazonEKSAdminViewPolicy with the access entry
resource "aws_eks_access_policy_association" "target_cluster_admin_view_policy" {
  cluster_name  = var.target_cluster_name
  principal_arn = aws_iam_role.mcp_access_role.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminViewPolicy"
  
  access_scope {
    type = "cluster"
  }
}

# Associate AmazonEKSViewPolicy with the access entry
resource "aws_eks_access_policy_association" "target_cluster_view_policy" {
  cluster_name  = var.target_cluster_name
  principal_arn = aws_iam_role.mcp_access_role.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"
  
  access_scope {
    type = "cluster"
  }
} 
