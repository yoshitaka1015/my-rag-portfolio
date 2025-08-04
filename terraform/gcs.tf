# terraform/gcs.tf

resource "google_storage_bucket" "source" {
  name                          = "${var.source_bucket_name}-${var.environment}"
    location                    = var.region
    uniform_bucket_level_access = true
    force_destroy               = true
}

resource "google_storage_bucket" "output" {
  name                          = "${var.output_bucket_name}-${var.environment}"
    location                    = var.region
    uniform_bucket_level_access = true
    force_destroy               = true
}