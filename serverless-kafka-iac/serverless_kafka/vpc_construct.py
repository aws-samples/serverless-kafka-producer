# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging as log

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

log.basicConfig(level=log.INFO)


KAFKA_VPC_NAME = "KafkaVPC"


class KafkaVPCS(Construct):
    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        subnets = [
            ec2.SubnetConfiguration(
                name="private-subnet-",
                cidr_mask=24,
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
            ),
            ec2.SubnetConfiguration(
                name="public-subnet-",
                cidr_mask=24,
                subnet_type=ec2.SubnetType.PUBLIC,
            ),
        ]
        
        self.vpc = ec2.Vpc(
            self,
            KAFKA_VPC_NAME,
            nat_gateways=1,
            max_azs=3,
            cidr="10.0.0.0/16",
            subnet_configuration=subnets
        )

        log_group = logs.LogGroup(self, "kafka-vpc-flowlogs", retention=logs.RetentionDays.ONE_DAY)

        role:iam.IRole = iam.Role(self, "VpcFlowLogRole", assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"))  # type: ignore


        self.vpc.add_flow_log("vpcflowlog", destination=ec2.FlowLogDestination.to_cloud_watch_logs(log_group=log_group, iam_role=role))



    def get_vpc(self) -> ec2.IVpc:
        return self.vpc
