variable "project_id" {
  description = "ID del proyecto en Google Cloud"
  type        = string
  default     = "mi-proyecto-ia"
}

variable "region" {
  description = "Region de GCP para los recursos"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "Nombre del cluster de GKE"
  type        = string
  default     = "cve-cluster"
}
