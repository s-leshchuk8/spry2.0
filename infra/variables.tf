variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}

variable "project_name" {
  type        = string
  default     = "spry"
  description = "Name of the project"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment name (dev, stage, prod)"
}

variable "google_client_id" {
  type        = string
  description = "Google OAuth Client ID"
  default     = ""
}

variable "google_client_secret" {
  type        = string
  description = "Google OAuth Client Secret"
  sensitive   = true
  default     = ""
}