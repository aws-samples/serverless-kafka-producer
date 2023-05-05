# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging as log

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_msk as msk
from constructs import Construct

from .helpers import allow_tcp_ports_to_internally

log.basicConfig(level=log.INFO)


class MSKCuster(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kafka_vpc: ec2.IVpc,
    ) -> None:
        super().__init__(scope, construct_id)

        vpc = kafka_vpc

        kafka_security_group = self.init_kafka_security_group(vpc=vpc)

        self.kafka_cluster = self.init_kafka_cluster(vpc, kafka_security_group)

        self.kafka_security_group = kafka_security_group

    @property
    def get_kafka_cluster(self) -> msk.CfnServerlessCluster:
        return self.kafka_cluster

    @property
    def get_kafka_security_group(self) -> ec2.ISecurityGroup:
        return self.kafka_security_group

    def init_kafka_security_group(self, vpc: ec2.IVpc):
        kafka_security_group = ec2.SecurityGroup(
            self,
            "kafka_client_security_group",
            vpc=vpc,
            description="kafka client security group"
        )


        allow_tcp_ports_to_internally(kafka_security_group.connections, [(2181, "Default Zookeeper"), (2182, "TLS Zookeeper"), (9098, "IAM Access")])

        return kafka_security_group

    def init_kafka_cluster(
        self, vpc_stack: ec2.IVpc, security_group: ec2.ISecurityGroup
    ) -> msk.CfnServerlessCluster:

        logs.LogGroup(self,"MSKExampleBrokerLogs", retention=logs.RetentionDays.ONE_DAY)

        logging_info_property = msk.CfnCluster.LoggingInfoProperty(
            broker_logs=msk.CfnCluster.BrokerLogsProperty(
                cloud_watch_logs=msk.CfnCluster.CloudWatchLogsProperty(
                    enabled=True,
                    log_group="MSKExampleBrokerLogs"
                )
            )
        )

        kafka_cluster = msk.CfnServerlessCluster(
            self,
            id="demo-cluster",
            cluster_name="demo-cluster",
            vpc_configs=[msk.CfnServerlessCluster.VpcConfigProperty(
                subnet_ids=vpc_stack.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
                ).subnet_ids,

                # the properties below are optional
                security_groups=[security_group.security_group_id]
            )],
            client_authentication=msk.CfnServerlessCluster.ClientAuthenticationProperty(
                sasl=msk.CfnServerlessCluster.SaslProperty(
                    iam=msk.CfnServerlessCluster.IamProperty(enabled=True),
                )
            ),
        )

        return kafka_cluster
