# variable.tf
variable "project_id" {
  type        = string
  description = "GCPのプロジェクトID"
}

variable "region" {
  type        = string
  description = "リソースを作成するGCPのリージョン"
  default     = "asia-northeast1" # asia-northeast1 から変更
}

variable "source_bucket_name" {
  type        = string
  description = "入力用GCSバケットの名前"
}

variable "output_bucket_name" {
  type        = string
  description = "出力用GCSバケットの名前"
}

variable "function_name" {
  type        = string
  description = "Cloud Functionの名前"
  default     = "ocr-function-iac"
}
