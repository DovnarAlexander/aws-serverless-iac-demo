#!python

import os
import sys

if not os.getenv("AWS_ACCESS_KEY_ID", None) or not os.getenv("AWS_SECRET_ACCESS_KEY", None):
    print("Please check that AWS credentials are exported to env")
    sys.exit(1)
