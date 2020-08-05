variable "bot_token" {}

locals {
  telegram = local.source.telegram
}

resource "telegram_bot_commands" "this" {
  commands = [
    for command, data in local.telegram : {
      command     = command,
      description = data.description
    }
  ]
}

resource "telegram_bot_webhook" "this" {
  url = format(
    "https://api.telegram.org/bot%s/setWebHook?url=%s",
    var.bot_token, aws_api_gateway_deployment.this.invoke_url
  )
  allowed_updates = ["message", "callback_query"]
}
