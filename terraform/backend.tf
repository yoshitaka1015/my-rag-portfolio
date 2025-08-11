# terraform/backend.tf
# tfstateをCloud Storageに格納するために使う

terraform {
  backend "gcs" {
    bucket = "bkt-serious-timer-467517-e1-tfstate"
    prefix = "terraform/state"
  }
}