# terraform/cloud_function.tf

# FunctionのソースコードをZIP化
data "archive_file" "source" {
  type        = "zip"
  source_dir  = "../ocr-function"
  output_path = "/tmp/ocr-function.zip"
}

# ZIPファイルをGCSにアップロード
resource "google_storage_bucket_object" "source_zip" {
  name   = "source/ocr-function-${var.environment}-${data.archive_file.source.output_md5}.zip"
  bucket = google_storage_bucket.source.name
  source = data.archive_file.source.output_path
}

# Cloud Function 本体
resource "google_cloudfunctions2_function" "ocr_function" {
  name     = "${var.function_name}-${var.environment}"
  location = var.region

  build_config {
    runtime     = "python311"
    entry_point = "process_document"
    source {
      storage_source {
        bucket = google_storage_bucket.source.name
        object = google_storage_bucket_object.source_zip.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    min_instance_count = 0
    available_memory   = "1Gi"
    timeout_seconds    = 300
    environment_variables = {
      OUTPUT_BUCKET_NAME = google_storage_bucket.output.name
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"
    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.source.name
    }
  }

  # API有効化、ZIPアップロード、そして全ての関連権限付与が完了するのを待つ
  depends_on = [
    google_project_service.apis,
    google_storage_bucket_object.source_zip,
    google_project_iam_member.gcs_to_pubsub,      # 正しいリソース名に修正
    google_project_iam_member.eventarc_service_agent # 正しいリソース名に修正
  ]
}