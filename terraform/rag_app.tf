# terraform/rag_app.tf

# 1. Cloud Runサービスに割り当てるサービスアカウント
resource "google_service_account" "rag_app_sa" {
  account_id   = "rag-app-sa"
  display_name = "Service Account for RAG App"
}

# 3. appディレクトリのソースコードからハッシュ値を計算
data "archive_file" "app_source" {
  type        = "zip"
  source_dir  = "../app" # Dockerfileもこの中にあることを想定
  output_path = "/tmp/rag-app-source.zip"
}

# 4. ソースコードのハッシュを使って、一意なDockerイメージ名を定義
locals {
  image_url = "${var.region}-docker.pkg.dev/${var.project_id}/my-app-repo/rag-app:${data.archive_file.app_source.output_sha256}"
}

# 5. gcloudコマンドを実行して、ビルドとプッシュを行うリソース
resource "null_resource" "build_and_push_rag_app" {
  # appディレクトリのコード内容が変わるたびに、このリソースを再作成（コマンドを再実行）する
  triggers = {
    source_sha = data.archive_file.app_source.output_sha256
  }

  # このコマンドは、あなたのローカルPC上で実行される
  provisioner "local-exec" {
    command = "gcloud builds submit ../app --tag ${local.image_url}"
  }
}

# 6. ビルド完了後、60秒待機するリソース
resource "time_sleep" "wait_for_image_propagation" {
  # ソースコードのハッシュ値が変わるたびに、この待機処理も再実行する
  triggers = {
    source_sha = data.archive_file.app_source.output_sha256
  }
  
  create_duration = "60s"

  # ビルドとプッシュが完了してから待機を開始する
  depends_on = [null_resource.build_and_push_rag_app]
}

# 7. RAGアプリ用のCloud Runサービス本体
resource "google_cloud_run_v2_service" "rag_app" {
  name                = "rag-portfolio-app-iac"
  location            = var.region
  deletion_protection = false

  template {
    # サービスアカウントはカスタムのものに戻すのが最終形です
    service_account = google_service_account.rag_app_sa.email

    containers {
      image = local.image_url
      ports {
        container_port = 8080
      }
    }
  }

  # 60秒の待機が完了してからデプロイを開始するように修正
  depends_on = [
    time_sleep.wait_for_image_propagation
  ]
}

# 8. Cloud Runサービスを公開設定にする
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.rag_app.name
  location = google_cloud_run_v2_service.rag_app.location
  project  = google_cloud_run_v2_service.rag_app.project
  role     = "roles/run.invoker"
  member   = "allUsers"
}
