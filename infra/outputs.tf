output "user_pool_id" {
  value       = try(aws_cognito_user_pool.main.id, "")
  description = "Cognito User Pool ID"
}

output "user_pool_client_id" {
  value       = try(aws_cognito_user_pool_client.client.id, "")
  description = "Cognito User Pool Client ID"
}

output "reports_bucket_name" {
  value       = try(aws_s3_bucket.reports.bucket, "")
  description = "S3 bucket name for weekly reports"
}