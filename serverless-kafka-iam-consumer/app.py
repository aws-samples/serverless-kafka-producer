# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json


def lambda_handler(event, context):

    print (event)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": event,
            }
        ),
    }
