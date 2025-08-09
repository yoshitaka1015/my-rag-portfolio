# 変数定義（環境差分は environment で切り替える）

variable "project_id" {
  type        = string
  description = "GCP のプロジェクト ID"
  default     = "serious-timer-467517-e1"
}

variable "region" {
  type        = string
  description = "GCP のリージョン（Cloud Run / Eventarc など）"
  default     = "us-central1"
}

variable "source_bucket_name" {
  type        = string
  description = "OCR 入力用バケットのベース名（環境サフィックスは自動付与）"
  default     = "bkt-serious-timer-467517-e1-rag-source"
}

variable "output_bucket_name" {
  type        = string
  description = "OCR 出力 / ベクトルデータ用バケットのベース名（環境サフィックスは自動付与）"
  default     = "bkt-serious-timer-467517-e1-rag-output"
}

variable "function_name" {
  type        = string
  description = "OCR 用 Cloud Run サービスのベース名"
  default     = "ocr-function"
}

variable "environment" {
  type        = string
  description = "環境名（例: staging / prod）"
}
