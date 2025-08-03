# terraform/main.tf

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "project" {}

# --------------------------------------------------------------
# APIの有効化
# --------------------------------------------------------------
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudfunctions.googleapis.com",
    "eventarc.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "aiplatform.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}