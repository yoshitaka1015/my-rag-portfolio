# terraform/backend.tf
# tfstateをCloud Storageに格納するために使う

terraform {
  backend "gcs" {
    bucket = "tfstate-serious-timer-467517-e1"
    prefix = "terraform/state"
  }
}