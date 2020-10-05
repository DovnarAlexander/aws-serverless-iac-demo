locals {
  data = yamldecode(file(format("%s/../data.yaml", path.module)))
  iam =  local.data["iam"]
  vars = local.data["terraform"]
}