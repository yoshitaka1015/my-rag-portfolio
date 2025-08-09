# Terraformで利用する変数定義
# - 既定値は安全に動くデフォルトを設定
# - 環境差分は -var で上書き可能

variable "project_id" {
  type        = string
  description = "GCPのプロジェクトID"
  default     = "serious-timer-467517-e1"
}

variable "region" {
  type        = string
  description = "リソースを作成するGCPのリージョン（例: us-central1）"
  default     = "us-central1"  # ← 統一
}

variable "source_bucket_name" {
  type        = string
  description = "OCR用のソースファイルを格納するバケット名（環境サフィックスは別途付与）"
  default     = "bkt-serious-timer-467517-e1-rag-source"
}

variable "output_bucket_name" {
  type        = string
  description = "OCR処理結果を格納するバケット名（環境サフィックスは別途付与）"
  default     = "bkt-serious-timer-467517-e1-rag-output"
}

variable "function_name" {
  type        = string
  description = "Cloud Functionの基本名（環境サフィックスは別途付与）"
  default     = "ocr-function"
}

variable "environment" {
  type        = string
  description = "デプロイする環境名（例: staging, prod など）"
}

terraform {
  required_version = ">= 1.0"

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
