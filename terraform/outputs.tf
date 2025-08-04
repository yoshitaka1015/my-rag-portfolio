# terraform/outputs.tf

output "rag_app_url" {
  value       = google_cloud_run_v2_service.rag_app.uri
  description = "The URL of the deployed RAG application."
}
