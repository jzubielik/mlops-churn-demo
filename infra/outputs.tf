# Root outputs — what `terraform output` shows after `apply`.

output "platform_name" {
  description = "Full, unique churn platform name (with a random id)."
  value       = local.platform_full
}

output "platform_suffix" {
  description = "Random, human-readable name suffix (random_pet)."
  value       = local.name_suffix
}

output "platform_id" {
  description = "Random hex platform identifier (random_id)."
  value       = local.platform_id
}

output "platform_manifest_path" {
  description = "Path to the main platform manifest."
  value       = local_file.platform_manifest.filename
}

output "environments" {
  description = "Map of environment -> key paths/names created by the module."
  value = {
    for env, mod in module.ml_env : env => {
      bucket_name   = mod.bucket_name
      bucket_path   = mod.bucket_path
      config_path   = mod.config_path
      registry_path = mod.registry_path
    }
  }
}
