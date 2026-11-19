output "cluster_name" {
  description = "Nombre del cluster GKE creado"
  value       = google_container_cluster.primary.name
}

output "kubernetes_endpoint" {
  description = "Endpoint del cluster para conectar kubectl y helm"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "get_credentials_command" {
  description = "Comando para configurar kubectl hacia este cluster"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region} --project ${var.project_id}"
}

output "models_bucket_url" {
  description = "URL del bucket de Cloud Storage para modelos"
  value       = google_storage_bucket.models_bucket.url
}

output "artifact_registry_repo" {
  description = "Path completo al repositorio de Artifact Registry"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.cve_repo.repository_id}"
}
