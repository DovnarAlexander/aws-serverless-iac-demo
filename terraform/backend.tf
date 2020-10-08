terraform {
  required_version = "~> 0.12"
  required_providers {
    aws = {
      version = "~> 3.0"
    }
  }
  backend "s3" {
    bucket  = "cloudevescops-zdays-demo"
    encrypt = true
    key     = "terraform.tfstate"
    region  = "us-east-1"
    # Locking
    dynamodb_table = "cloudevescops-zdays-demo"
  }
}

provider "aws" {
  region = "us-east-1"
}
