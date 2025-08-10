# 変数定義（環境差分は environment で切り替える）

variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for Cloud Run"
  default     = "us-central1"
}

# 環境名（例: staging / prod）
variable "environment" {
  type        = string
  description = "Environment name (e.g., staging, prod)"
}

# ベクトルデータの格納先バケット名。
# 空のときは 'bkt-<project>-rag-output-<environment>' を自動採用（localsで算出）。
variable "vector_bucket_name" {
  type        = string
  description = "GCS bucket name for vector data (.jsonl)"
  default     = ""
}

# Artifact Registry のリポジトリ名（コンテナ格納先）
variable "artifact_repo" {
  type        = string
  description = "Artifact Registry repository name"
  default     = "rag-portfolio-repo"
}

# Cloud Run のスケール設定
variable "min_instance_count" {
  type        = number
  description = "Minimum number of Cloud Run instances"
  default     = 0
}
variable "max_instance_count" {
  type        = number
  description = "Maximum number of Cloud Run instances"
  default     = 10
}
