# terraform/backend.tf

terraform {
  backend "gcs" {
    bucket = "bkt-serious-timer-467517-e1-tfstate"
    prefix = "terraform/state"
  }
}