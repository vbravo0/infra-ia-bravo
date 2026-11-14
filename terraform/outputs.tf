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
