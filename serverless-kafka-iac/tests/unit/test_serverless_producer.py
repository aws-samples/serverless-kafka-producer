# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import logging as log

import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest
from aws_cdk import Aspects
from aws_cdk.aws_lambda import Function
from cdk_nag import AwsSolutionsChecks
from constructs import Construct, IConstruct
from serverless_kafka.demo_stack import KafkaDemoBackendStack
from serverless_kafka.serverless_producer_stack import (
    CUSTOM_RESOURCE_PHYISCAL_FUNCTION_NAME, ServerlessKafkaProducerStack)

from .test_helpers import add_resource_suppressions

log.basicConfig(level=log.INFO)

'''
ServerlessKafkaProducerStack
├─ KafkaProducer LambdaFunction
├─ messagesapiendpoint API Gateway
├─ kafkaclicall AWS CustomResource to read the Bootstrap URL of the MSK cluster and assign it as Environment variable  
├─ lambda which gets created as part of a the function construct to change the log retention period
├─ lambda function as part of the CustomResource construct to read the bootstrap url
'''
@pytest.fixture(scope="session")
def demo_stack() -> ServerlessKafkaProducerStack:

    app = core.App()

    backend_stack = KafkaDemoBackendStack(app, "kafkaBackendDemoStack", "messages")

    kafka_producer = ServerlessKafkaProducerStack(
        app,
        "teststack",
        backend_stack.kafka_vpc,
        backend_stack.kafka_security_group,
        backend_stack.msk_arn,
        "messages",
    )

    producer_function = kafka_producer.node.find_child("KafkaProducer")
    producer_function_supressions = [
        (
            "AwsSolutions-IAM5",
            "Access to describe all groups is required to push message to kafka, furthermore to read the bootstrap server url from an CLI call as part of the provisionging",
        ),
        (
            "AwsSolutions-IAM4",
            "We are using the AWS Managed LambdaExecutingRole, LambdaVPCAccessExecutingRole",
        ),
        (
            "AwsSolutions-L1",
            "We are using the Runtime Java 11 the code was tested and build with",
        ),
    ]
    add_resource_suppressions(producer_function, producer_function_supressions)
    

    api_gw = kafka_producer.node.find_child("messagesapiendpoint")
    api_gw_supressions = [
        (
            "AwsSolutions-APIG1",
            "This a short living non productive example appliction, thus we do not need access logging",
        ),
        (
            "AwsSolutions-IAM4",
            "We are using the AWS Managed PushToCloudWatchLogs, LambdaVPCAccessExecutingRole",
        ),
        ("AwsSolutions-APIG3", "It is a example application, API will only "),
        (
            "AwsSolutions-APIG2",
            "We do not use request validation for the example ping pong application ",
        ),
        ("AwsSolutions-APIG4", "We do not use authorization for APIGW"),
        (
            "AwsSolutions-COG4",
            "This a short living non productive example (ping/pong) appliction. The application does not store any type of data there is nothing which needs to be protected",
        ),
    ]
    add_resource_suppressions(api_gw, api_gw_supressions)


    sdk_cli_call = kafka_producer.node.find_child("kafkaclicall")
    sdk_cli_call_supression = [
        (
            "AwsSolutions-IAM4",
            "We are using the AWS Managed LambdaExecutingRole for CLI call",
        ),
        (
            "AwsSolutions-L1",
            "We are using the Runtime Java 11 the code was tested and build with",
        ),
    ]
    add_resource_suppressions(sdk_cli_call, sdk_cli_call_supression)



    custom_resource_cdk_lambda = find_custom_ressource_lambda(kafka_producer)
    custom_resource_cdk_supressions = [
        (
            "AwsSolutions-IAM4",
            "We are using the AWS Managed AWSLambdaBasicExecutionRole for CLI call",
        ),
        (
            "AwsSolutions-IAM5",
            "The AWS Managed AWSLambdaBasicExecutionRole has a * rule for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup",
        ),
        (
            "AwsSolutions-L1",
            "We are using the runtime provided by the CustomRuntime Construct",
        ),
    ]
    add_resource_suppressions(custom_resource_cdk_lambda, custom_resource_cdk_supressions)


    customer_log_retention_resource = find_custom_resource_log_retention(kafka_producer)
    customer_log_retention_resource_supressions = [
        (
            "AwsSolutions-IAM4",
            "We are using the AWS Managed AWSLambdaBasicExecutionRole for CLI call",
        ),
        (
            "AwsSolutions-IAM5",
            "The AWS Managed AWSLambdaBasicExecutionRole has a * rule for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup",
        ),
    ]
    add_resource_suppressions(customer_log_retention_resource, customer_log_retention_resource_supressions)

    Aspects.of(kafka_producer).add(AwsSolutionsChecks(verbose=True))
    return kafka_producer

def find_custom_ressource_lambda(_node:IConstruct):
    for child in _node.node.children:
        if isinstance(child, Function) and child._physical_name == CUSTOM_RESOURCE_PHYISCAL_FUNCTION_NAME:
            return child

    raise Exception('Could not find Custom resource CLI call Lambda')
   

def find_custom_resource_log_retention(_node:IConstruct):
    for child in _node.node.children:
        if isinstance(child, Construct) and child.node.id.startswith('LogRetention'):
            return child
    
    raise Exception('Could not find Custom resource for LogRetention')

def test_serverless_producer_stack_warnings(demo_stack):

    warnings = assertions.Annotations.from_stack(demo_stack).find_warning(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )

    log.error(warnings)

    assert not warnings


def test_serverless_producer_stack_errors(demo_stack):

    error = assertions.Annotations.from_stack(demo_stack).find_error(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )

    log.error(error)

    assert not error
