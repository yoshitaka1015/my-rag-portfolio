# RAGアプリ用のCloud Runサービス定義
# - サービス名は rag-portfolio-app-<環境>
# - 初期イメージはus-central1/Artifact Registryを指す（本番デプロイ時はGitHub Actionsからdigestで更新）
# - 実行サービスアカウントは iam.tf で定義した rag_app_sa を使用
# - 公開アクセス（roles/run.invoker を allUsers に付与）

resource "google_cloud_run_v2_service" "rag_app" {
  name     = "rag-portfolio-app-${var.environment}"
  location = var.region

  template {
    service_account = google_service_account.rag_app_sa.email

    containers {
      # 初期イメージ（後続のCIでdigestに更新される想定）
      image = "us-central1-docker.pkg.dev/${var.project_id}/rag-portfolio-repo/rag-portfolio-app:initial"
      ports {
        container_port = 8080
      }

      # 必要であれば環境変数等をここに定義
      # env {
      #   name  = "ENV"
      #   value = var.environment
      # }
    }

    # スケーリング、CPU/メモリ等の基本設定（必要に応じて変更）
    scaling {
      min_instance_count = 0  # コールドスタート許容（後で1以上に変更可）
      max_instance_count = 10
    }
  }

  # IAMロールの設定などが完了してから作成されるように依存関係を明示
  depends_on = [google_project_iam_member.rag_app_sa_roles]
}

# Cloud Runサービスを公開にする（誰でもアクセス可）
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.rag_app.name
  location = google_cloud_run_v2_service.rag_app.location
  project  = google_cloud_run_v2_service.rag_app.project
  role     = "roles/run.invoker"
  member   = "allUsers"
}
