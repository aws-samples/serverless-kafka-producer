# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging as log

from aws_cdk import CfnOutput
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct

from .helpers import get_group_name, get_topic_name

log.basicConfig(level=log.INFO)


class BastionHost(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kafka_vpc: ec2.IVpc,
        msk_cluster_arn: str,
        region: str,
        kafka_cluster_security_group: ec2.ISecurityGroup,
        topic_name: str,
    ) -> None:
        super().__init__(scope, construct_id)

        vpc = kafka_vpc

        kafka_bastion_host_security_group = self.init_kafka_bastion_host_security_group(
            vpc=vpc
        )

        bastion_host = self.init_bastion_host(
            vpc=vpc,
            kafka_cluster_arn=msk_cluster_arn,
            region=region,
            kafka_bastion_host_security_group=kafka_bastion_host_security_group,
            kafka_cluster_security_group=kafka_cluster_security_group,
            topic_name=topic_name,
        )

    def init_bastion_host(
        self,
        vpc: ec2.IVpc,
        kafka_cluster_arn: str,
        kafka_bastion_host_security_group: ec2.ISecurityGroup,
        kafka_cluster_security_group: ec2.ISecurityGroup,
        region: str,
        topic_name: str,
    ):

        kafka_bastion_host_instance = ec2.Instance(
            self,
            "bastion_host",
            vpc=vpc,
            instance_type=ec2.InstanceType("t2.micro"),
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
            ),
            security_group=kafka_bastion_host_security_group,
            machine_image=ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),block_devices=[
                ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(8,
                    encrypted=True
                ))
            ]
        )

        output = CfnOutput(
            self,
            "bastionoutput",
            value=kafka_bastion_host_instance.instance_id,
            description="Bastion host id",
            export_name="BastionHostIp",
        )

        kafka_bastion_host_instance.add_user_data(
            "yum update -y",
            "yum install -y java-11-amazon-corretto-headless",  # install a trusted jre
            "cd /home/ec2-user/",
            "wget https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip",  # upgrade to aws cli v2 to get bootstrap information
            "wget https://github.com/aws/aws-msk-iam-auth/releases/download/v1.1.3/aws-msk-iam-auth-1.1.3-all.jar",  # download the iam authenticator
            "wget https://archive.apache.org/dist/kafka/2.6.3/kafka_2.13-2.6.3.tgz",  # download the kafka client
            "unzip awscli-exe-linux-x86_64.zip",
            "tar -xvf kafka_2.13-2.6.3.tgz",
            "./aws/install",
            "PATH=/usr/local/bin:$PATH",
            "source ~/.bash_profile",
            f'echo "TLS=$(aws kafka describe-cluster --cluster-arn {kafka_cluster_arn} --query "ClusterInfo.ZookeeperConnectString" --region {region})" >> /etc/environment',
            f'echo "ZK=$(aws kafka get-bootstrap-brokers --cluster-arn {kafka_cluster_arn} --query "BootstrapBrokerStringSaslIam" --region {region})" >> /etc/environment',
            'echo "CLASSPATH=/home/ec2-user/aws-msk-iam-auth-1.1.3-all.jar" >> /etc/environment',
            "cd kafka_2.13-2.6.3/bin/",
            'echo "security.protocol=SASL_SSL" >> client.properties',
            'echo "sasl.mechanism=AWS_MSK_IAM" >> client.properties',
            'echo "sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;" >> client.properties',
            'echo "sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler" >> client.properties',
            "./kafka-topics.sh --bootstrap-server $ZK --command-config client.properties --create --replication-factor 3 --partitions 3 --topic messages",  # create event topic
        )

        access_kafka_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka:ListClusters",
                "kafka:GetBootstrapBrokers",
                "kafka:DescribeCluster",
                "kafka-cluster:Connect",
                "kafka-cluster:AlterCluster",
            ],
            resources=[kafka_cluster_arn],
        )

        admin_kafka_topics = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka-cluster:WriteData",
                "kafka-cluster:ReadData",
                "kafka-cluster:*Topic*",
            ],
            resources=[
                get_topic_name(
                    kafka_cluster_arn=kafka_cluster_arn, topic_name="messages"
                )
            ],
        )

        access_to_user_groups = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["kafka-cluster:AlterGroup", "kafka-cluster:DescribeGroup"],
            resources=[
                get_group_name(kafka_cluster_arn=kafka_cluster_arn, group_name="*")
            ],
        )

        

        kafka_bastion_host_instance.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        kafka_bastion_host_instance.add_to_role_policy(access_kafka_policy)
        kafka_bastion_host_instance.add_to_role_policy(admin_kafka_topics)
        kafka_bastion_host_instance.add_to_role_policy(access_to_user_groups)

        self.allow_bastion_host_to_access_kafka(
            kafka_cluster_security_group, kafka_bastion_host_security_group
        )

        return kafka_bastion_host_instance

    def init_kafka_bastion_host_security_group(self, vpc: ec2.IVpc):
        kafka_bastion_host_sg = ec2.SecurityGroup(
            self,
            "kafka_bastion_host_sg",
            vpc=vpc,
            description="kafka client security group"
        )

        return kafka_bastion_host_sg

    def allow_bastion_host_to_access_kafka(
        self, kafka_sg: ec2.ISecurityGroup, bastion_host_sg: ec2.ISecurityGroup
    ):

       
        kafka_sg.connections.allow_from(other=bastion_host_sg.connections, port_range=ec2.Port.tcp(9098))

        
        return None
