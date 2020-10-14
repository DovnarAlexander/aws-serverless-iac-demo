resource "aws_iam_role" "lambda" {
  name               = "lambda-terraform"
  assume_role_policy = jsonencode(local.iam.assume)
}

resource "aws_iam_role_policy" "lambda" {
  role   = aws_iam_role.lambda.id
  name   = "dummy"
  policy = jsonencode(local.iam.policy)
}
