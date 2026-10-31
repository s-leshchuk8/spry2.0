# ADR 001: Migration from AWS CloudFormation to Terraform & HCP Terraform

* **Status:** Accepted
* **Date:** 2026-10-31

## Context
Previously, infrastructure management was based on AWS CloudFormation templates. To achieve better infrastructure modularity, cross-provider flexibility, and automated remote state management with drift detection, a transition to Terraform and HCP Terraform was required.

## Decision
We decided to:
1. Replace all AWS CloudFormation templates with declarative Terraform code stored in the `infra/` directory.
2. Connect the GitHub repository `spry2.0` with HCP Terraform (Workspace `spry2-dev`).
3. Manage secrets and AWS credentials via HCP Terraform Environment Variables.

## Consequences
* **Pros:** Automated speculative runs on PRs/commits, centralized remote state tracking, unified IaC workflow.
* **Cons:** Requires managing HCP Terraform Workspace configuration and variable synchronization.
