# Terraform コアとプロバイダの要件。ここで必要なプロバイダを宣言する。
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    # Google Cloud の公式プロバイダ
    google = {
      source  = "hashicorp/google"
      version = "~> 5.36"
    }
    # 一部の先行機能（必要に応じて利用）
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.36"
    }
    # ローカルのファイル/ディレクトリを zip などに固めるユーティリティ
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

# Google プロバイダの共通設定。変数からプロジェクトとリージョンを受け取る。
provider "google" {
  project = var.project_id
  region  = var.region
}

# ベータ版プロバイダの共通設定。
provider "google-beta" {
  project = var.project_id
  region  = var.region
}
