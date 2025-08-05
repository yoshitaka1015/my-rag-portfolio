# terraform/iam.tf

data "google_project" "project" {}

# --------------------------------------------------------------
# Service Accounts
# --------------------------------------------------------------
resource "google_service_account" "rag_app_sa" {
  account_id   = "rag-app-sa-${var.environment}"
  display_name = "Service Account for RAG App (${var.environment})"
}

# --------------------------------------------------------------
# IAM Permissions
# --------------------------------------------------------------

# --- Cloud Function Trigger Permissions ---
resource "google_project_iam_member" "gcs_to_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "eventarc_service_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}

# --- RAG Application Permissions ---
resource "google_project_iam_member" "rag_app_sa_roles" {
  for_each = toset([
    "roles/storage.objectViewer",
    "roles/aiplatform.user",
    "roles/aiplatform.serviceAgent"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.rag_app_sa.email}"

  depends_on = [google_service_account.rag_app_sa]
}

# Eventarcサービスエージェントに、ソースバケットを直接読み取る権限を付与
resource "google_storage_bucket_iam_member" "eventarc_can_read_source_bucket" {
  bucket = google_storage_bucket.source.name
  role   = "roles/storage.objectViewer" # ← 正しいロールに修正
  member = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}

# IAM権限がGCP全体に反映されるのを待つための、60秒の待機時間
resource "time_sleep" "wait_for_iam_propagation" {
  create_duration = "60s"

  # すべてのIAM権限設定が完了してから、待機を開始する
  depends_on = [
    google_project_iam_member.gcs_to_pubsub,
    google_project_iam_member.eventarc_service_agent,
    google_project_iam_member.rag_app_sa_roles
  ]
}