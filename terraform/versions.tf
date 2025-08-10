# Terraform 本体と使用するプロバイダの宣言
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    # Google プロバイダ（既存Stateと整合が取れるよう広めに許容）
    google = {
      source  = "hashicorp/google"
      version = ">= 5.50, < 7.0"
    }
    # 一部の先行機能で利用することがあるため揃えて保持
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.50, < 7.0"
    }
    # data "archive_file" などを使う場合に必要
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    # 旧Stateに time_sleep が残っているため取得（後で掃除可）
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13"
    }
  }
}

# 共通のプロバイダ設定（変数は TF_VAR_* で与える）
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
