# Module outputs — the root can further aggregate and display them.

output "environment" {
  description = "Name of the environment handled by the module."
  value       = var.environment
}

output "bucket_name" {
  description = "Logical name of the artifacts bucket."
  value       = local.bucket_name
}

output "bucket_path" {
  description = "On-disk path representing the artifacts bucket."
  value       = local.bucket_path
}

output "config_path" {
  description = "Path to the environment configuration file."
  value       = local_file.env_config.filename
}

output "registry_path" {
  description = "Path to the model registry configuration."
  value       = local_file.model_registry.filename
}
