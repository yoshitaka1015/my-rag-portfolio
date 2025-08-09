// 変数定義

variable "project_id" {
  type        = string
  description = "GCPのプロジェクトID"
  default     = "serious-timer-467517-e1"
}

variable "region" {
  type        = string
  description = "GCPリージョン"
  default     = "us-central1"
}

variable "source_bucket_name" {
  type        = string
  description = "OCR入力用バケット名"
  default     = "bkt-serious-timer-467517-e1-rag-source"
}

variable "output_bucket_name" {
  type        = string
  description = "OCR出力用バケット名"
  default     = "bkt-serious-timer-467517-e1-rag-output"
}

variable "function_name" {
  type        = string
  description = "Cloud Function のベース名"
  default     = "ocr-function"
}

variable "environment" {
  type        = string
  description = "環境名（例: staging / prod）"
}
