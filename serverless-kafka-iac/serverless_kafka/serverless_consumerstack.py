# Copyright 2023 klosep
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging as log
import os
import uuid
from pathlib import Path

from aws_cdk import (BundlingOptions, BundlingOutput, DockerVolume, Duration,
                     Names, Stack)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as f
from aws_cdk import aws_logs as logs
from aws_cdk.aws_lambda_event_sources import ManagedKafkaEventSource
from constructs import Construct

from .helpers import get_group_name, get_paramter, get_topic_name

P_RESERVED_CONCURRENCY = "P_RESERVED_CONCURRENCY"
P_MAX_CONCURRENCY = "P_MAX_CONCURRENCY"

LAMBDA_TIMEOUT_SECONDS = 15

CUSTOM_RESOURCE_PHYISCAL_FUNCTION_NAME = "kafkaCLICallFunction"

log.basicConfig(level=log.INFO)


class ServerlessKafkaConsumerStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kafka_vpc: ec2.IVpc,
        kafka_security_group: ec2.ISecurityGroup,
        msk_arn: str,
        topic_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.init_kafka_consumer_lambda(
            vpc=kafka_vpc,
            kafka_security_groud=kafka_security_group,
            msk_arn=msk_arn,
            topic_name=topic_name,
        )

    def init_kafka_consumer_lambda(
        self,
        vpc: ec2.IVpc,
        kafka_security_groud: ec2.ISecurityGroup,
        msk_arn: str,
        topic_name: str,
    ):
        consumer_function = f.Function(
            self,
            "KafkaConsumer",
            runtime=f.Runtime.JAVA_17,  # type: ignore
            handler="aws.samples.kafka.lambdaconsumer.App::handleRequest",
            timeout=Duration.seconds(LAMBDA_TIMEOUT_SECONDS),
            log_retention=logs.RetentionDays.ONE_DAY,
            code=self.build_mvn_package(),
            tracing=f.Tracing.DISABLED,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
            ),
            security_groups=[kafka_security_groud],
            reserved_concurrent_executions=get_paramter(
                self.node, P_MAX_CONCURRENCY, 60
            ),
            environment={
                "JAVA_TOOL_OPTIONS": "-XX:+TieredCompilation -XX:TieredStopAtLevel=1",
                "POWERTOOLS_LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "KafkaConsumer",
            },
            memory_size=1024,
        )

        consumer_group_id = str(uuid.uuid4())

        consumer_function.add_event_source(
            ManagedKafkaEventSource(
                cluster_arn=msk_arn,
                topic=topic_name,
                batch_size=100,
                consumer_group_id=consumer_group_id,
                starting_position=f.StartingPosition.TRIM_HORIZON,
            )
        )

        access_kafka_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka-cluster:Connect",
                "kafka-cluster:DescribeGroup",
                "kafka-cluster:AlterGroup",
                "kafka-cluster:DescribeTopic",
                "kafka-cluster:ReadData",
                "kafka-cluster:ReadGroup",
                "kafka-cluster:DescribeClusterDynamicConfiguration"
            ],
            resources=[get_group_name(msk_arn, consumer_group_id), get_topic_name(msk_arn, 'messages'), msk_arn]
        )

        consumer_function.add_to_role_policy(access_kafka_policy)

        

    def build_mvn_package(self):
        home = str(Path.home())

        log.info("Building Java Project using M2 home from")
        m2_home = os.path.join(home, ".m2/")
        log.info(f"M2_home={m2_home}")

        code = f.Code.from_asset(
            path=os.path.join("..", "serverless-kafka-iam-consumer"),
            bundling=BundlingOptions(
                image=f.Runtime.JAVA_17.bundling_image,
                command=[
                    "/bin/sh",
                    "-c",
                    "mvn clean install -q -Dmaven.test.skip=true && cp /asset-input/target/KafkaConsumer.zip /asset-output/",
                ],
                user="root",
                output_type=BundlingOutput.ARCHIVED,
                volumes=[DockerVolume(host_path=m2_home, container_path="/root/.m2/")],
            ),
        )
        return code
