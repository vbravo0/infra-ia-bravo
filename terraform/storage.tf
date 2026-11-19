# Bucket de Cloud Storage para almacenar los modelos versionados (Consigna 2.3)
resource "google_storage_bucket" "models_bucket" {
  name                     = var.models_bucket_name
  location                 = var.region
  force_destroy            = false
  public_access_prevention = "enforced"

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true
}

# Repositorio en Artifact Registry para las imagenes inmutables de Docker (Clase 3 y 8)
resource "google_artifact_registry_repository" "cve_repo" {
  location      = var.region
  repository_id = "cve-repo"
  description   = "Repositorio Docker para imagenes del modelo CVE"
  format        = "DOCKER"
}
