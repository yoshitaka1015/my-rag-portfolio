# terraform/versions.tf

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    # このブロックを追加
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9"
    }
  }
}