#!/usr/bin/env python

import yaml
from aws_cdk import core
from serverless.main import Main


# Read yaml vars
with open("../data.yaml", 'r') as stream:
    data = yaml.safe_load(stream)
_vars = data["cdk"]
_iam = data["iam"]

app = core.App()
Main(app, "cdk", data=_vars, iam_vars=_iam)

app.synth()
