# ml_environment module variables — creates a set of artifacts for ONE environment.

variable "environment" {
  description = "Environment name (e.g. dev, stage, prod)."
  type        = string
}

variable "platform_name" {
  description = "ML platform name — common resource prefix."
  type        = string
}

variable "model_name" {
  description = "Model name in the registry (e.g. churn-clf)."
  type        = string
}

variable "suffix" {
  description = "Random/unique suffix ensuring name uniqueness (from the root)."
  type        = string
}

variable "root_dir" {
  description = "Directory in which the module creates environment artifacts."
  type        = string
}

variable "model_registry_format" {
  description = "Model registry configuration format (informational, used in the file name)."
  type        = string
  default     = "json"
}
