terraform {
  required_version = ">= 1.10"

cloud {
    organization = "ooad-solomiia"

    workspaces {
      name = "spry2-dev"
    }
  }


  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      PROJECT_NAME = var.project_name
      ManagedBy    = "terraform"
      Environment  = var.environment
    }
  }
}