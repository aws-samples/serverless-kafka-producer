# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2

from serverless_kafka.demo_stack import KafkaDemoBackendStack
from serverless_kafka.helpers import get_paramter
from serverless_kafka.serverless_producer_stack import ServerlessKafkaProducerStack

# CLI Options
KAFKA_VPC_ID = "KAFKA_VPC_ID"
KAFKA_SECURITY_GROUP_ID = "KAFKA_SECURITY_GROUP_ID"
MODE = "MODE"
STANDALONE = "STANDALONE"
MSK_ARN = "MSK_ARN"
TOPIC_NAME = "TOPIC_NAME"


app = cdk.App()


kafka_backend = KafkaDemoBackendStack(
    app,
    "KafkaDemoBackendStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
    topic_name=get_paramter(app.node, TOPIC_NAME, 'messages')
)


kafka_vpc = kafka_backend.kafka_vpc
kafka_security_group = kafka_backend.kafka_security_group
msk_arn = kafka_backend.msk_arn
mode = app.node.try_get_context(MODE)
if mode == STANDALONE:
    kafka_vpc = ec2.Vpc.from_lookup(
        app, "existingvpc", vpc_id=app.node.try_get_context(KAFKA_VPC_ID)
    )
    kafka_security_group = ec2.SecurityGroup.from_security_group_id(
        app,
        "existingsecuritygroup",
        security_group_id=app.node.try_get_context(KAFKA_SECURITY_GROUP_ID),
    )
    msk_arn = app.node.try_get_context(MSK_ARN)


serverless = ServerlessKafkaProducerStack(
    app,
    "ServerlessKafkaProducerStack",
    kafka_vpc=kafka_vpc,
    kafka_security_group=kafka_security_group,
    msk_arn=msk_arn,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
    topic_name=get_paramter(app.node, TOPIC_NAME, 'messages')
)

#Aspects.of(app).add(AwsSolutionsChecks(verbose=True))
app.synth()
