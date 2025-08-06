# terraform/rag_app.tf

# RAGアプリ用のCloud Runサービス本体
resource "google_cloud_run_v2_service" "rag_app" {
  name     = "rag-portfolio-app-${var.environment}"
  location = var.region
  deletion_protection = false # この設定を確認・追加

  template {
    service_account = google_service_account.rag_app_sa.email

    containers {
      image = "asia-northeast1-docker.pkg.dev/${var.project_id}/my-app-repo/rag-app:v1" # 手動ビルドしたイメージを指定
      ports {
        container_port = 8080
      }
      env {
        name  = "VECTOR_BUCKET_NAME"
        value = google_storage_bucket.output.name
    }
  }

  # 権限付与が終わってからデプロイするように依存関係を設定
  depends_on = [google_project_iam_member.rag_app_sa_roles]
}

# Cloud Runサービスを公開設定にする
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.rag_app.name
  location = google_cloud_run_v2_service.rag_app.location
  project  = google_cloud_run_v2_service.rag_app.project
  role     = "roles/run.invoker"
  member   = "allUsers"
}