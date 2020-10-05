#!/usr/bin/env python

import yaml
import json
import shutil
import pulumi
import pulumi_aws as aws

# Read yaml vars
with open("../data.yaml", 'r') as stream:
    data = yaml.safe_load(stream)
_vars = data["pulumi"]
_iam = data["iam"]
# VPC
main = aws.ec2.Vpc("main", cidr_block=_vars["vpc"])
azs = aws.get_availability_zones(state="available")
igw = aws.ec2.InternetGateway("gw", vpc_id=main.id)
public_route = aws.ec2.RouteTable(
    "publicRouteTable",
    vpc_id=main.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )
    ]
)
public_subnets = []
for i, s in enumerate(_vars["subnets"]["public"]):
    subnet = aws.ec2.Subnet(
        "public-{}".format(s), vpc_id=main.id, cidr_block=s, availability_zone=azs.names[i]
    )
    public_subnets.append(subnet)
    aws.ec2.RouteTableAssociation("public-{}".format(s), subnet_id=subnet.id, route_table_id=public_route.id)
nat_ip = aws.ec2.Eip("nat")
nat_gw = aws.ec2.NatGateway("gw", allocation_id=nat_ip.id, subnet_id=subnet)
private_route = aws.ec2.RouteTable(
    "privateRouteTable",
    vpc_id=main.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            nat_gateway_id=nat_gw.id,
        )
    ]
)
private_subnets = []
for i, s in enumerate(_vars["subnets"]["private"]):
    subnet = aws.ec2.Subnet(
        "private-{}".format(s), vpc_id=main.id, cidr_block=s, availability_zone=azs.names[i]
    )
    private_subnets.append(subnet)
    aws.ec2.RouteTableAssociation("private-{}".format(s), subnet_id=subnet.id, route_table_id=private_route.id)
# Security groups
lb_sg = aws.ec2.SecurityGroup("lb", description="LB SG",vpc_id=main.id)
lambda_sg = aws.ec2.SecurityGroup("lambda", description="Lambda SG",vpc_id=main.id)
# Load Balancer
_sg_rules = [
    {
        'sg': lb_sg.id,
        'rules': [
            {
                "direction": "ingress",
                "description": "HTTP from Internet",
                "from_port": 80,
                "to_port": 80,
                "protocol": "tcp",
                "cidr_blocks": ["0.0.0.0/0"]
            },
            {
                "direction": "egress",
                "description": "LB to Lambda",
                "from_port": 80,
                "to_port": 80,
                "protocol": "tcp",
                "source_security_group_id": lambda_sg.id
            }
        ]
    },
    {
        "sg": lambda_sg.id,
        "rules": [
            {
                "direction": "ingress",
                "description": "HTTP from LB",
                "from_port": 80,
                "to_port": 80,
                "protocol": "tcp",
                "source_security_group_id": lb_sg.id
            },
            {
                "direction": "egress",
                "description": "All to Internet",
                "from_port": 0,
                "to_port": 65535,
                "protocol": "tcp",
                "cidr_blocks": ["0.0.0.0/0"]
            }
        ]
    }
]
for ruleset in _sg_rules:
    for rule in ruleset["rules"]:
        aws.ec2.SecurityGroupRule(
            rule["description"],
            type=rule["direction"],
            to_port=rule["to_port"],
            from_port=rule["from_port"],
            protocol=rule["protocol"],
            security_group_id=ruleset["sg"],
            cidr_blocks=rule["cidr_blocks"] if "cidr_blocks" in rule else None,
            source_security_group_id=rule["source_security_group_id"] if "source_security_group_id" in rule else None,
            self=rule["self"] if "self" in rule else None
        )
# IAM
role = aws.iam.Role("lambda-pulumi", path="/", assume_role_policy=json.dumps(_iam["assume"]))
aws.iam.RolePolicy("lambda", role=role.id, policy=json.dumps(_iam["policy"]))
# Lambda
shutil.make_archive("../lambda", 'zip', "../lambda/")
function = aws.lambda_.Function(
    resource_name="lambda-pulumi",
    code="../lambda.zip",
    handler="lambda.lambda_handler",
    runtime="python3.8",
    role=role.arn,
    vpc_config={
        "subnet_ids": [s.id for s in private_subnets],
        "security_group_ids": [lambda_sg.id]
    },
    environment={
        "variables": {
            "TOOL": "Pulumi"
        }
    }
)
# LB
lb = aws.lb.LoadBalancer(
    "lb-pulumi", load_balancer_type="application",
    subnets=[s.id for s in public_subnets],
    security_groups=[lb_sg.id], internal=False
)
alb_tg = aws.lb.TargetGroup(
    "lambda-pulumi", target_type="lambda",
    health_check={
        "enabled": True,
        "path": "/",
        "matcher": 200,
        "timeout": 30,
        "interval": 40
    }
)
aws.lambda_.Permission(
    "load-balancer", action="lambda:InvokeFunction",function=function.id,
    principal="elasticloadbalancing.amazonaws.com"
)
aws.lb.TargetGroupAttachment("lambda", target_group_arn=alb_tg.arn, target_id=function.arn)
aws.lb.Listener(
    "lambda", load_balancer_arn=lb.arn, port=80, protocol="HTTP",
    default_actions=[{
        "type": "forward",
        "target_group_arn": alb_tg.arn
    }]
)
# Export to output
pulumi.export("fqdn", lb.dns_name)