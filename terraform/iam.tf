# terraform/iam.tf

# --------------------------------------------------------------
# IAM Permissions
# --------------------------------------------------------------

# GCSトリガーがPub/Subを利用するための権限
resource "google_project_iam_member" "pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# RAGアプリのサービスアカウント(rag-app-sa)に必要な権限を付与
resource "google_project_iam_member" "rag_app_sa_roles" {
  for_each = toset([
    "roles/storage.objectViewer",    # GCSバケットの読み取り権限
    "roles/aiplatform.user",         # Vertex AIの基本利用権限
    "roles/aiplatform.serviceAgent"  # Vertex AIのサービスエージェント権限
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.rag_app_sa.email}"

  # サービスアカウントが作成されてから権限を付与する
  depends_on = [google_service_account.rag_app_sa]
}