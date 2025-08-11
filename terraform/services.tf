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
  project  = var.project_id

  template {
    # 実行サービスアカウント
    service_account = local.rag_sa_email

    # リビジョンに付与する論理ラベル（監視・課金分析・検索のため）
    labels = {
      app         = "rag-portfolio-app"
      environment = var.environment
    }

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
    prevent_destroy = true
    ignore_changes = [
      # テンプレート内の“CD側で動く”差分
      template[0].containers[0].image,  # CD が digest 指定で更新
      template[0].labels,               # managed-by, commit-sha など
      template[0].service_account,
      template[0].containers[0].ports,

      # ルート属性でズレが出やすいもの
      deletion_protection,

      # gcloud デプロイ時の付帯情報
      client, client_version
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
  project  = var.project_id

  template {
    # 実行サービスアカウント（RAG と共通 SA を想定）
    service_account = local.rag_sa_email

    # リビジョンに付与する論理ラベル（監視・課金分析・検索のため）
    labels = {
      app         = "ocr-function"
      environment = var.environment
    }

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
    prevent_destroy = true
    ignore_changes = [
      template[0].containers[0].image,
      template[0].labels,
      template[0].service_account,
      template[0].containers[0].ports,

      deletion_protection,

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
# GCS: ベクトル/出力バケット（prod のみ作成）
# - staging は既存を import して運用しているため、ここでは prod のみ新規作成に限定
# - 既定の命名規則：bkt-<project>-rag-output-<environment>
# ─────────────────────────────────────────────────────────────────────────────
resource "google_storage_bucket" "vector" {
  count   = var.environment == "prod" ? 1 : 0
  name    = local.vector_bucket
  project = var.project_id
  location = var.region

  # U B L A を有効化（IAMはバケットレベルで管理）
  uniform_bucket_level_access = true

  # 明示的に破棄しない運用を基本にする
  force_destroy = false

  # ここでは最低限の設定に留める（ライフサイクル等は必要になったら追加）
}

# ─────────────────────────────────────────────────────────────────────────────
# GCS: RAG アプリの実行 SA へ、ベクトル/出力バケットの閲覧権限を付与（加算）
# ─────────────────────────────────────────────────────────────────────────────
resource "google_storage_bucket_iam_member" "output_viewer_for_rag_app" {
  bucket = try(google_storage_bucket.vector[0].name, local.vector_bucket)
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.rag_sa_email}"
}

# ─────────────────────────────────────────────────────────────────────────────
# IAM: GitHub Actions 実行SA → RAG 実行SA の ActAs（本番のみ）
# - Cloud Run デプロイ時に、GitHub Actions 側のSAが実行SAを "actAs" できるようにする。
# - 環境が prod のときだけ適用する（staging では不要）。
# ─────────────────────────────────────────────────────────────────────────────
resource "google_service_account_iam_member" "runner_can_actas_rag_sa" {
  # 対象となる実行サービスアカウント（メールアドレス指定）
  service_account_id = "projects/${var.project_id}/serviceAccounts/${local.rag_sa_email}"

  # actAs 権限
  role   = "roles/iam.serviceAccountUser"

  # GitHub Actions 側のデプロイ用サービスアカウント
  member = "serviceAccount:github-actions-runner@${var.project_id}.iam.gserviceaccount.com"

  # 本番のみ有効化
  count  = var.environment == "prod" ? 1 : 0
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