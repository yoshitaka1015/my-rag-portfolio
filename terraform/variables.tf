# terraform/variables.tf

variable "project_id" {
  type        = string
  description = "GCPのプロジェクトID"
  default     = "serious-timer-467517-e1"
}

variable "region" {
  type        = string
  description = "リソースを作成するGCPのリージョン"
  default     = "asia-northeast1"
}

variable "source_bucket_name" {
  type        = string
  description = "入力用GCSバケットの基本名"
  default     = "bkt-serious-timer-467517-e1-rag-source"
}

variable "output_bucket_name" {
  type        = string
  description = "出力用GCSバケットの基本名"
  default     = "bkt-serious-timer-467517-e1-rag-output"
}

variable "function_name" {
  type        = string
  description = "Cloud Functionの基本名"
  default     = "ocr-function"
}

variable "environment" {
  type        = string
  description = "デプロイする環境名 (prod, stagingなど)"
}