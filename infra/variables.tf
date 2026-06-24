# Root input variables. Override the defaults in terraform.tfvars.

variable "platform_name" {
  description = "Churn ML platform name — common prefix for all resources."
  type        = string
  default     = "churn-platform"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.platform_name))
    error_message = "platform_name: lowercase letters/digits/hyphens, 3-31 characters, starts with a letter."
  }
}

variable "model_name" {
  description = "Model name in the registry (consistent with MLflow: churn-clf)."
  type        = string
  default     = "churn-clf"
}

variable "environment" {
  description = "Primary environment (controls, among others, output naming)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "stage", "prod"], var.environment)
    error_message = "environment must be one of: dev, stage, prod."
  }
}

variable "environments" {
  description = "List of environments for which the module creates a full set of files."
  type        = list(string)
  default     = ["dev", "stage"]
}

variable "output_root" {
  description = "Base directory where all local infrastructure artifacts are created."
  type        = string
  default     = "build"
}

variable "owner" {
  description = "Owner/team recorded in the platform metadata."
  type        = string
  default     = "mlops-team"
}
