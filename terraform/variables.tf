variable "project_id" {
  description = "ID del proyecto en Google Cloud"
  type        = string
  default     = "unlu-ia-bravo"
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

variable "models_bucket_name" {
  description = "Nombre del bucket de Cloud Storage para almacenar los modelos versionados"
  type        = string
  default     = "unlu-ia-bravo-models"
}
