from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_lambda as lmd,
    aws_elasticloadbalancingv2 as alb,
    core
)
import json
import shutil
import boto3
class Main(core.Stack):

    def __init__(self, scope: core.Construct, id: str, data, iam_vars) -> None:
        super().__init__(scope, id)
        # VPC
        vpc = ec2.CfnVPC(self, "cdk-vpc", cidr_block=data["vpc"])
        igw = ec2.CfnInternetGateway(self, id="igw")
        ec2.CfnVPCGatewayAttachment(self, id="igw-attach", vpc_id=vpc.ref, internet_gateway_id=igw.ref)
        public_route_table = ec2.CfnRouteTable(self, id="public_route_table", vpc_id=vpc.ref)
        ec2.CfnRoute(
            self, id="public_route", route_table_id=public_route_table.ref,
            destination_cidr_block="0.0.0.0/0", gateway_id=igw.ref
        )
        public_subnets = []
        for i, s in enumerate(data["subnets"]["public"]):
            subnet = ec2.CfnSubnet(
                self, id="public_{}".format(s), cidr_block=s,
                vpc_id = vpc.ref, availability_zone = core.Fn.select(i, core.Fn.get_azs()), map_public_ip_on_launch=True
            )
            public_subnets.append(subnet)
            ec2.CfnSubnetRouteTableAssociation(
                self, id="public_{}_association".format(s),
                route_table_id=public_route_table.ref, subnet_id=subnet.ref
            )
        eip = ec2.CfnEIP(self, id="natip")
        nat = ec2.CfnNatGateway(
            self, id="nat", allocation_id=eip.attr_allocation_id, subnet_id=public_subnets[0].ref
        )
        private_route_table = ec2.CfnRouteTable(self, id="private_route_table", vpc_id=vpc.ref)
        ec2.CfnRoute(
            self, id="private_route", route_table_id=private_route_table.ref,
            destination_cidr_block="0.0.0.0/0", nat_gateway_id=nat.ref
        )
        private_subnets = []
        for i, s in enumerate(data["subnets"]["private"]):
            subnet = ec2.CfnSubnet(
                self, id="private_{}".format(s), cidr_block=s,
                vpc_id = vpc.ref, availability_zone = core.Fn.select(i, core.Fn.get_azs()), map_public_ip_on_launch=False
            )
            private_subnets.append(subnet)
            ec2.CfnSubnetRouteTableAssociation(
                self, id="private_{}_association".format(s),
                route_table_id=private_route_table.ref, subnet_id=subnet.ref
            )
        # Security groups
        lb_sg = ec2.CfnSecurityGroup(self, id="lb", group_description="LB SG", vpc_id=vpc.ref)
        lambda_sg = ec2.CfnSecurityGroup(self, id="lambda", group_description="Lambda SG", vpc_id=vpc.ref)
        public_prefix = ec2.CfnPrefixList(
            self, id="cidr_prefix", address_family="IPv4", max_entries=1,
            prefix_list_name="public", entries=[{"cidr": "0.0.0.0/0", "description": "Public"}]
        )
        _sg_rules = [
            {
                'sg': lb_sg.attr_group_id,
                'rules': [
                    {
                        "direction": "ingress",
                        "description": "HTTP from Internet",
                        "from_port": 80,
                        "to_port": 80,
                        "protocol": "tcp",
                        "cidr_blocks": public_prefix.ref
                    },
                    {
                        "direction": "egress",
                        "description": "LB to Lambda",
                        "from_port": 80,
                        "to_port": 80,
                        "protocol": "tcp",
                        "source_security_group_id": lambda_sg.attr_group_id
                    }
                ]
            },
            {
                "sg": lambda_sg.attr_group_id,
                "rules": [
                    {
                        "direction": "ingress",
                        "description": "HTTP from LB",
                        "from_port": 80,
                        "to_port": 80,
                        "protocol": "tcp",
                        "source_security_group_id": lb_sg.attr_group_id
                    },
                    {
                        "direction": "egress",
                        "description": "All to Internet",
                        "from_port": 0,
                        "to_port": 65535,
                        "protocol": "tcp",
                        "cidr_blocks": public_prefix.ref
                    }
                ]
            }
        ]
        for ruleset in _sg_rules:
            for rule in ruleset["rules"]:
                if rule["direction"] == "ingress":
                    ec2.CfnSecurityGroupIngress(
                        self, id=rule["description"].replace(" ", "_"),
                        description=rule["description"],
                        to_port=rule["to_port"],
                        from_port=rule["from_port"],
                        ip_protocol=rule["protocol"],
                        group_id=ruleset["sg"],
                        source_prefix_list_id=rule["cidr_blocks"] if "cidr_blocks" in rule else None,
                        source_security_group_id=rule["source_security_group_id"] if "source_security_group_id" in rule else None
                    )
                else:
                    ec2.CfnSecurityGroupEgress(
                        self, id=rule["description"].replace(" ", "_"),
                        description=rule["description"],
                        to_port=rule["to_port"],
                        from_port=rule["from_port"],
                        ip_protocol=rule["protocol"],
                        group_id=ruleset["sg"],
                        destination_prefix_list_id=rule["cidr_blocks"] if "cidr_blocks" in rule else None,
                        destination_security_group_id=rule["source_security_group_id"] if "source_security_group_id" in rule else None
                    )
        # IAM
        assume_policy_doc = iam.PolicyDocument()
        for statement in iam_vars["assume"]["Statement"]:
            _statement = iam.PolicyStatement(
                actions=[statement["Action"]],
            )
            _statement.add_service_principal(statement["Principal"]["Service"])
            assume_policy_doc.add_statements(_statement)
        role = iam.CfnRole(
            self, id="iam_role", path="/", assume_role_policy_document=assume_policy_doc
        )
        role_policy_doc = iam.PolicyDocument()
        for statement in iam_vars["policy"]["Statement"]:
            _statement = iam.PolicyStatement(
                actions=statement["Action"],
                resources=["*"]
            )
            role_policy_doc.add_statements(_statement)
        policy = iam.CfnPolicy(
            self, id="iam_policy", policy_document=role_policy_doc,
            policy_name="cdkPolicy", roles=[role.ref]
        )
        # Lambda
        shutil.make_archive("../lambda", 'zip', "../lambda/")
        s3_client = boto3.client('s3')
        s3_client.upload_file("../lambda.zip", "cloudevescops-zdays-demo", "cdk.zip")
        function = lmd.CfnFunction(
            self, id="lambda_function", handler="lambda.lambda_handler",
            role=role.attr_arn, runtime="python3.7",
            code={
                "s3Bucket": "cloudevescops-zdays-demo",
                "s3Key": "cdk.zip"
            },
            vpc_config={
                "securityGroupIds": [lambda_sg.ref],
                "subnetIds": [s.ref for s in private_subnets]
            },
            environment={
                "variables": {
                    "TOOL": "CDK"
                }
            }
        )
        # LB
        lb = alb.CfnLoadBalancer(
            self, id="alb", name="lb-cdk", scheme="internet-facing", type="application",
            subnets=[s.ref for s in public_subnets],
            security_groups=[lb_sg.ref]
        )
        lmd.CfnPermission(
            self, id="lambda_permis", action="lambda:InvokeFunction",
            function_name=function.ref, principal="elasticloadbalancing.amazonaws.com"
        )
        tg = alb.CfnTargetGroup(
            self, id="alb_tg", name="lambda-cdk", target_type="lambda",
            health_check_enabled=True, health_check_interval_seconds=40,
            health_check_path="/", health_check_timeout_seconds=30,
            targets=[{"id": function.get_att("Arn").to_string()}],
            matcher={"httpCode": "200"}
        )
        alb.CfnListener(
            self, id="listener", default_actions=[{"type": "forward",
            "targetGroupArn": tg.ref}],
            load_balancer_arn=lb.ref, port=80, protocol="HTTP"
        )
        core.CfnOutput(self, id="fqdn", value=lb.attr_dns_name)
