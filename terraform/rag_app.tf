# RAGアプリ用のCloud Run(v2)サービス定義
# - ここでは土台（命名/リージョン/ポート/スケール）を定義
# - 実際のイメージはCI/CDでdigest指定デプロイされ上書きされる

resource "google_cloud_run_v2_service" "rag_app" {
  # サービス名は環境サフィックスで分離（例: rag-portfolio-app-staging / rag-portfolio-app-prod）
  name     = "rag-portfolio-app-${var.environment}"
  # リージョン統一
  location = var.region

  template {
    # 実行用サービスアカウント（最小権限の専用SAを推奨）
    service_account = google_service_account.rag_app_sa.email

    containers {
      # 初期イメージ参照（ブートストラップ用）
      image = "us-central1-docker.pkg.dev/${var.project_id}/rag-portfolio-repo/rag-portfolio-app:v1"

      # アプリの待受ポート（一般的に 8080）
      ports {
        container_port = 8080
      }

      # リソース制限（初期値の目安：RAGはメモリが膨らみやすい）
      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }

      # 必要に応じて環境変数（定数/Secret参照）を追加
      # env { name = "APP_ENV"; value = var.environment }
      # env {
      #   name = "OPENAI_API_KEY"
      #   value_source {
      #     secret_key_ref {
      #       secret  = google_secret_manager_secret.openai_api_key.secret_id
      #       version = "latest"
      #     }
      #   }
      # }
    }

    # 1インスタンスの同時処理数（高すぎると遅延増、低すぎると台数増）
    max_instance_request_concurrency = 30

    # オートスケール：min=0（コールドスタート許容）、maxは必要に応じて調整
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }

  # 入口はインターネット到達を許可（認証有無はデプロイ時フラグ/IAMで制御）
  ingress = "INGRESS_TRAFFIC_ALL"
}
