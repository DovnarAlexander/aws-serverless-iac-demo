locals {
  source = yamldecode(file("../application.yaml"))
}
