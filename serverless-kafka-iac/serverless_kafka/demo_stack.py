# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging as log

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

from serverless_kafka.bastion_construct import BastionHost
from serverless_kafka.msk_cluster_construct import MSKCuster
from serverless_kafka.vpc_construct import KafkaVPCS

log.basicConfig(level=log.INFO)


class KafkaDemoBackendStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, topic_name: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.tags.set_tag("app", "kafka-serverless")

        kafka_construct = KafkaVPCS(self, "kafka-vpc")

        self.kafka_vpc = kafka_construct.vpc

        msk = MSKCuster(self, "msk", kafka_vpc=self.kafka_vpc)

        self.msk_arn = msk.kafka_cluster.attr_arn

        self.kafka_security_group = msk.kafka_security_group

        bastion_host = BastionHost(
            self,
            "bastionhost",
            region=self.region,
            kafka_vpc=self.kafka_vpc,
            msk_cluster_arn=self.msk_arn,
            kafka_cluster_security_group=self.kafka_security_group,
            topic_name=topic_name,
        )

    
    @property
    def get_msk_arn(self) -> str:
        return self.msk_arn

    @property
    def get_kafka_vpc(self) -> ec2.IVpc:
        return self.kafka_vpc

    @property
    def get_kafka_security_group(self) -> ec2.ISecurityGroup:
        return self.kafka_security_group
