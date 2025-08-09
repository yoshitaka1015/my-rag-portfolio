// Terraform本体とプロバイダのバージョン/設定

terraform {
  required_version = ">= 1.3.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9"
    }
  }
}

// Google プロバイダの共通設定
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "time" {}
