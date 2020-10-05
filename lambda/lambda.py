#!env python

import os
import urllib.request
import json

def lambda_handler(event, context):
    response = {
        "statusCode": 200,
        "statusDescription": "200 OK",
        "isBase64Encoded": False,
        "headers": {
            "Content-Type": "text/html; charset=utf-8"
        }
    }
    with urllib.request.urlopen("https://official-joke-api.appspot.com/jokes/programming/random") as r:
        data = json.loads(r.read())
    response['body'] = """<html>
<head>
<title>Hello From jokes!</title>
</head>
<body>
<h1>Hello from random Jokes (deployed with {0})!</h1>
<h2>{1}</h2>
<h3>{2}</h3>
</body>
</html>""".format(
        os.getenv("TOOL"),
        data[0]["setup"],
        data[0]["punchline"]
    )
    return response
