# Cloud Run と関連 IAM、GCS IAM を環境別に管理する。
# - プロジェクトレベルの API 有効化や Project IAM はここでは扱わない。
# - コンテナイメージは Terraform 側では固定タグ (:initial) を参照し、CD 側が digest で更新する。
#   ドリフトは lifecycle.ignore_changes で吸収する。

# ─────────────────────────────────────────────────────────────────────────────
# 共通ローカル値（命名・既定値）
# ─────────────────────────────────────────────────────────────────────────────
locals {
  # サービス名は <name>-<environment>
  rag_service_name = "rag-portfolio-app-${var.environment}"
  ocr_service_name = "ocr-function-${var.environment}"

  # 実行サービスアカウント（既存前提）
  rag_sa_email = "rag-app-sa-${var.environment}@${var.project_id}.iam.gserviceaccount.com"

  # ベクトル/出力バケット名：未指定なら規約名で補完
  vector_bucket = var.vector_bucket_name != "" ? var.vector_bucket_name : "bkt-${var.project_id}-rag-output-${var.environment}"

  # Artifact Registry のイメージ参照（Terraform側は固定タグ、CD が digest で更新）
  rag_image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repo}/rag-portfolio-app:initial"
  ocr_image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repo}/ocr-function:initial"
}

# ─────────────────────────────────────────────────────────────────────────────
# Cloud Run: RAG Web アプリ（公開）
# ─────────────────────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "rag_app" {
  name     = local.rag_service_name
  location = var.region

  template {
    # 実行サービスアカウント
    service_account = local.rag_sa_email

    containers {
      # Terraform では固定タグを保持。CD が digest を反映する。
      image = local.rag_image

      # 基本ENV
      env {
        name  = "REGION"
        value = var.region
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }

      # RAGアプリが参照するベクトルデータ（jsonl）置き場
      env {
        name  = "VECTOR_BUCKET_NAME"
        value = local.vector_bucket
      }

      # アプリの HTTP ポート（既定 8080）
      ports {
        container_port = 8080
      }
    }

    # スケール設定
    scaling {
      min_instance_count = var.min_instance_count
      max_instance_count = var.max_instance_count
    }
  }

  # 全世界から到達可能
  ingress = "INGRESS_TRAFFIC_ALL"

  # CD が更新する digest や付帯ラベル等のドリフトを無視
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,  # CD が digest 指定で更新
      template[0].labels,               # managed-by, commit-sha など
      client, client_version            # gcloud デプロイ時の付帯情報
    ]
  }
}

# 誰でも invoke 可能にする公開 IAM
resource "google_cloud_run_v2_service_iam_member" "rag_app_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.rag_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─────────────────────────────────────────────────────────────────────────────
# Cloud Run: OCR（ドキュメント処理）サービス（公開）
# ─────────────────────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "ocr_function" {
  name     = local.ocr_service_name
  location = var.region

  template {
    # 実行サービスアカウント（RAG と共通 SA を想定）
    service_account = local.rag_sa_email

    containers {
      image = local.ocr_image

      # 共通ENV
      env {
        name  = "REGION"
        value = var.region
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }

      # OCR が書き出す出力先（RAG と同一バケットを使う運用）
      env {
        name  = "OUTPUT_BUCKET_NAME"
        value = local.vector_bucket
      }

      ports {
        container_port = 8080
      }
    }

    scaling {
      min_instance_count = var.min_instance_count
      max_instance_count = var.max_instance_count
    }
  }

  ingress = "INGRESS_TRAFFIC_ALL"

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      template[0].labels,
      client, client_version
    ]
  }
}

resource "google_cloud_run_v2_service_iam_member" "ocr_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ocr_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─────────────────────────────────────────────────────────────────────────────
# GCS: RAG アプリの実行 SA へ、ベクトル/出力バケットの閲覧権限を付与（加算）
# ─────────────────────────────────────────────────────────────────────────────
resource "google_storage_bucket_iam_member" "output_viewer_for_rag_app" {
  bucket = local.vector_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.rag_sa_email}"
}

# ─────────────────────────────────────────────────────────────────────────────
# 出力（履歴で URL 確認用）※ outputs.tf は廃止し、ここへ統合
# ─────────────────────────────────────────────────────────────────────────────
output "rag_app_url" {
  value       = google_cloud_run_v2_service.rag_app.uri
  description = "RAG app (Cloud Run) URL"
}

output "ocr_function_url" {
  value       = google_cloud_run_v2_service.ocr_function.uri
  description = "OCR function (Cloud Run) URL"
}
