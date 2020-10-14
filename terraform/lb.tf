locals {
  lb_rules = {
    x = {
      type        = "ingress"
      description = "HTTP from Internet"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    },
    y = {
      type                     = "egress"
      description              = "LB to Lambda"
      from_port                = 80
      to_port                  = 80
      protocol                 = "tcp"
      source_security_group_id = aws_security_group.lambda.id
    }
  }
}

resource "aws_security_group" "lb" {
  name        = "lb"
  description = "LB SG"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group_rule" "lb" {
  for_each                 = local.lb_rules
  type                     = each.value.type
  from_port                = each.value.from_port
  to_port                  = each.value.to_port
  protocol                 = each.value.protocol
  cidr_blocks              = lookup(each.value, "cidr_blocks", null)
  source_security_group_id = lookup(each.value, "source_security_group_id", null)
  self                     = lookup(each.value, "self", null)
  security_group_id        = aws_security_group.lb.id
}

resource "aws_lb" "this" {
  name               = "lb-terraform"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb.id]
  subnets            = aws_subnet.public.*.id
}

resource "aws_lambda_permission" "allow_elb" {
  statement_id  = "load-balancer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "elasticloadbalancing.amazonaws.com"
}

resource "aws_lb_target_group" "lambda" {
  name        = "lambda"
  target_type = "lambda"
  health_check {
    enabled  = true
    path     = "/"
    matcher  = 200
    timeout  = 30
    interval = 40
  }
}

resource "aws_lb_target_group_attachment" "lambda" {
  target_group_arn = aws_lb_target_group.lambda.arn
  target_id        = aws_lambda_function.this.arn
  depends_on       = [aws_lambda_permission.allow_elb]
}

resource "aws_lb_listener" "this" {
  load_balancer_arn = aws_lb.this.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.lambda.arn
  }
}
