# terraform/versions.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.36"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.36"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    # State に time_sleep が残っているので取得が必要
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
