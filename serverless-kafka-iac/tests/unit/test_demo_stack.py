# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging as log

import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest
from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks
from serverless_kafka.demo_stack import KafkaDemoBackendStack

from .test_helpers import add_resource_suppressions

log.basicConfig(level=log.INFO)


@pytest.fixture(scope="session")
def demo_stack() -> KafkaDemoBackendStack:
    app = core.App()
    demo_stack = KafkaDemoBackendStack(app, "kafkaBackendDemoStack", "messages")

    bastion_host = demo_stack.node.find_child("bastionhost")

    bastion_host_supressions = [
        ("AwsSolutions-EC28", "Detailed logging for Bastion host is not required"),
        (
            "AwsSolutions-EC29",
            "As this is example code as part of blogpost termination protection is not required",
        ),
        (
            "AwsSolutions-IAM4",
            "Since this is an non productive example, using AWS managed policies is valid",
        ),
        (
            "AwsSolutions-IAM5",
            "We are allowing the bastion user to fully control Kafka Topics, as this is an non productive example",
        ),
    ]

    add_resource_suppressions(bastion_host, bastion_host_supressions)
   

    msk_cluster = demo_stack.node.find_child("msk")
    msk_supressions = [
        (
            "AwsSolutions-MSK6",
            "As this an example blogpost cluster we do not require broker logs",
        )
    ]

    add_resource_suppressions(msk_cluster, msk_supressions)
  
    Aspects.of(demo_stack).add(AwsSolutionsChecks(verbose=True))
    return demo_stack


def test_kafka_backend_demo_stack_no_warnings(demo_stack): 

    warnings = assertions.Annotations.from_stack(demo_stack).find_warning(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )

    log.error(warnings)

    assert not warnings


def testest_kafka_backend_demo_stack_no_errors(demo_stack):
    
    errors = assertions.Annotations.from_stack(demo_stack).find_error(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )

    log.error(errors)

    assert not errors
