# ml_environment module — a reusable "churn ML environment" expressed as files.
#
# For each environment it creates:
#   - a "bucket" directory for model artifacts (stand-in for S3/GCS),
#   - a .gitkeep file so the empty directory is tangible,
#   - model registry configuration (stand-in for the MLflow registry),
#   - an environment configuration file (JSON) with names and paths.
#
# The module does NOT use cloud providers — only hashicorp/local.

terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = ">= 2.5"
    }
  }
}

locals {
  bucket_name   = "${var.platform_name}-${var.environment}-artifacts-${var.suffix}"
  bucket_path   = "${var.root_dir}/${var.environment}/artifacts"
  registry_path = "${var.root_dir}/${var.environment}/model-registry.${var.model_registry_format}"
  config_path   = "${var.root_dir}/${var.environment}/env-config.json"
}

# "Bucket" for model artifacts = local directory (represents an S3/GCS bucket).
resource "local_file" "bucket_keep" {
  filename = "${local.bucket_path}/.gitkeep"
  content  = "# placeholder for the churn model artifacts bucket (${var.environment})\n"
}

# Model registry configuration (stand-in for the MLflow model registry).
resource "local_file" "model_registry" {
  filename = local.registry_path
  content = jsonencode({
    environment    = var.environment
    model_name     = var.model_name
    registry_uri   = "file://${local.bucket_path}/registry"
    default_alias  = var.environment == "prod" ? "production" : "staging"
    artifact_store = "file://${local.bucket_path}"
  })
}

# Environment configuration file — what the ML application would read at startup.
resource "local_file" "env_config" {
  filename = local.config_path
  content = jsonencode({
    environment   = var.environment
    platform      = var.platform_name
    model_name    = var.model_name
    bucket_name   = local.bucket_name
    bucket_path   = local.bucket_path
    registry_path = local.registry_path
    suffix        = var.suffix
  })
}
