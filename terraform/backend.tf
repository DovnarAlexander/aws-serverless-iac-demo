terraform {
  required_version = "~> 0.12"
  required_providers {
    aws = {
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

provider "telegram" {}