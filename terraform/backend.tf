# This file is used to configure the backend for the Terraform code.
# The backend cannot use variables, so we need to hardcode the bucket and table names.

terraform {
  backend "s3" {
    bucket         = "sre-agent-terraform-state"
    key            = "terraform.tfstate"
    region         = "eu-west-2"  # Change this to match your AWS region
    dynamodb_table = "sre-agent-terraform-locks"
    encrypt        = true
  }
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "sre-agent-terraform-state"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "sre-agent-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
} 
