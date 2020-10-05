locals {
  lambda_rules = {
    x = {
      type = "ingress"
      description = "HTTP from LB"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      source_security_group_id = aws_security_group.lb.id
    },
    y = {
      type = "egress"
      description = "All to Internet"
      from_port   = 0
      to_port     = 65535
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }
}

resource "aws_security_group" "lambda" {
  name        = "lambda"
  description = "Lambda SG"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group_rule" "lambda" {
  for_each = local.lambda_rules
  type              = each.value.type
  from_port         = each.value.from_port
  to_port           = each.value.to_port
  protocol          = each.value.protocol
  cidr_blocks       = lookup(each.value, "cidr_blocks", null)
  source_security_group_id       = lookup(each.value, "source_security_group_id", null)
  self = lookup(each.value, "self", null)
  security_group_id = aws_security_group.lambda.id
}

data "archive_file" "this" {
  type        = "zip"
  source_dir  = format("%s/../lambda/", path.module)
  output_path = format("%s/lambda.zip", path.module)
}

resource "aws_lambda_function" "this" {
  filename         = data.archive_file.this.output_path
  function_name    = "lambda-terraform"
  source_code_hash = data.archive_file.this.output_base64sha256
  handler          = "lambda.lambda_handler"
  runtime          = "python3.8"
  role = aws_iam_role.lambda.arn

  vpc_config {
    subnet_ids         = aws_subnet.private.*.id
    security_group_ids = list(aws_security_group.lambda.id)
  }

  environment {
    variables = {
      TOOL = "Terraform"
    }
  }
}
