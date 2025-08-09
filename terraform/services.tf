# Cloud Run（RAG アプリ / OCR コンテナ）と付帯 IAM を 1 ファイルに統合
# - RAG アプリに VECTOR_BUCKET_NAME を注入（.jsonl の参照先）
# - OCR に OUTPUT_BUCKET_NAME を注入（.jsonl の出力先）
# - RAG アプリの実行 SA に出力バケットの閲覧権限（storage.objectViewer）を付与
# - 両サービスとも公開（roles/run.invoker を allUsers へ付与）
# - 初期イメージは "initial" タグ。実運用は CI/CD で digest へ更新する想定

#####################
# 派生値（locals）
#####################
locals {
  # 環境サフィックス付きバケット名（例: xxx-staging / xxx-prod）
  source_bucket = var.environment == "staging"
    ? "${var.source_bucket_name}-staging"
    : "${var.source_bucket_name}-prod"

  output_bucket = var.environment == "staging"
    ? "${var.output_bucket_name}-staging"
    : "${var.output_bucket_name}-prod"

  # Cloud Run 実行サービスアカウント（既存 SA を想定）
  # 例: rag-app-sa-staging@<project>.iam.gserviceaccount.com
  rag_app_sa_email = "rag-app-sa-${var.environment}@${var.project_id}.iam.gserviceaccount.com"
}

################################
# RAG アプリ（Streamlit）Cloud Run
################################
resource "google_cloud_run_v2_service" "rag_app" {
  name     = "rag-portfolio-app-${var.environment}"
  location = var.region

  template {
    service_account = local.rag_app_sa_email

    containers {
      # 初期イメージ（CI が digest で上書き）
      image = "us-central1-docker.pkg.dev/${var.project_id}/rag-portfolio-repo/rag-portfolio-app:initial"

      ports {
        container_port = 8080
      }

      # 画面が参照するベクトルデータの保存先
      env {
        name  = "VECTOR_BUCKET_NAME"
        value = local.output_bucket
      }

      # 一般的に利用する基本情報（将来の拡張用）
      env {
        name  = "REGION"
        value = var.region
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
    }

    # オートスケール（必要に応じて調整）
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }
}

# RAG アプリを公開
resource "google_cloud_run_v2_service_iam_member" "rag_app_public" {
  name     = google_cloud_run_v2_service.rag_app.name
  location = google_cloud_run_v2_service.rag_app.location
  project  = google_cloud_run_v2_service.rag_app.project
  role     = "roles/run.invoker"
  member   = "allUsers"
}

################################
# OCR コンテナ（Cloud Run）
################################
resource "google_cloud_run_v2_service" "ocr_function" {
  name     = "${var.function_name}-${var.environment}"
  location = var.region

  template {
    service_account = local.rag_app_sa_email

    containers {
      # 初期イメージ（CI が digest で上書き）
      image = "us-central1-docker.pkg.dev/${var.project_id}/rag-portfolio-repo/ocr-function:initial"

      ports {
        container_port = 8080
      }

      # OCR の出力先（.jsonl を書き込む先）
      env {
        name  = "OUTPUT_BUCKET_NAME"
        value = local.output_bucket
      }

      # 一般的に利用する基本情報
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "REGION"
        value = var.region
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }
}

# OCR を公開（手動実行や疎通確認に使う）
resource "google_cloud_run_v2_service_iam_member" "ocr_public" {
  name     = google_cloud_run_v2_service.ocr_function.name
  location = google_cloud_run_v2_service.ocr_function.location
  project  = google_cloud_run_v2_service.ocr_function.project
  role     = "roles/run.invoker"
  member   = "allUsers"
}

################################
# GCS バケット IAM（RAG アプリ → 出力 .jsonl の閲覧）
################################
resource "google_storage_bucket_iam_member" "output_viewer_for_rag_app" {
  bucket = local.output_bucket                       # 既存バケット名でも可（リソース管理外でも動作）
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.rag_app_sa_email}"
}

#####################
# 出力（URL など）
#####################
output "rag_app_url" {
  description = "RAG アプリ（Cloud Run）の URL"
  value       = google_cloud_run_v2_service.rag_app.uri
}

output "ocr_function_url" {
  description = "OCR コンテナ（Cloud Run）の URL"
  value       = google_cloud_run_v2_service.ocr_function.uri
}
