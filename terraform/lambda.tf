locals {
  zip = "../bot/function.zip"
}

resource "aws_lambda_function" "this" {
  filename         = local.zip
  function_name    = "lambda"
  source_code_hash = filebase64sha256(local.zip)
  handler          = "lambda.lambda_handler"
  runtime          = "python3.7"
  role             = aws_iam_role.this.arn

  environment {
    variables = {
      TELEGRAM_TOKEN = var.bot_token
    }
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowInvokeFromAPIGW"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = format("%s/*/*/*", aws_api_gateway_rest_api.this.execution_arn)
}