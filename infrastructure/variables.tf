variable "resource_group_name" {
  type        = string
  description = "Name of the Azure resource group"
}

variable "location" {
  type        = string
  description = "Azure region for all resources"
}

variable "environment" {
  type        = string
  description = "Environment label applied to resource tags (e.g. dev, staging, prod)"
  default     = "dev"
}

variable "cluster_name" {
  type        = string
  description = "Name of the AKS cluster"
}

variable "kubernetes_version" {
  type        = string
  description = "Kubernetes version for the AKS cluster"
}

variable "node_count" {
  type        = number
  description = "Initial node count in the default node pool"
  default     = 2
}

variable "node_vm_size" {
  type        = string
  description = "VM size for AKS nodes"
  default     = "Standard_D8s_v3"
}

variable "acr_name" {
  type        = string
  description = "Azure Container Registry name — must be globally unique, alphanumeric only"
}

variable "github_owner" {
  type        = string
  description = "GitHub username or organisation that owns the repository"
}

variable "github_repository" {
  type        = string
  description = "GitHub repository name (must already exist)"
}

variable "github_token" {
  type        = string
  description = "GitHub Personal Access Token with repo scope — used by Flux to push flux-system manifests"
  sensitive   = true
}
