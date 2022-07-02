# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging as log
import os
from pathlib import Path


from aws_cdk import (BundlingOptions, BundlingOutput, DockerVolume, Duration,
                     Stack)
from aws_cdk import aws_apigateway as apig
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as f
from aws_cdk import aws_logs as logs
from aws_cdk import custom_resources as cs
from constructs import Construct

from .helpers import get_group_name, get_paramter, get_topic_name

log.basicConfig(level=log.INFO)

# Template optional parameter
P_RESERVED_CONCURRENCY = "P_RESERVED_CONCURRENCY"
P_MAX_CONCURRENCY = "P_MAX_CONCURRENCY"

LAMBDA_TIMEOUT_SECONDS = 15

CUSTOM_RESOURCE_PHYISCAL_FUNCTION_NAME = 'kafkaCLICallFunction'


class ServerlessKafkaProducerStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kafka_vpc: ec2.IVpc,
        kafka_security_group: ec2.ISecurityGroup,
        msk_arn: str,
        topic_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = kafka_vpc

        bootstrap_broker = self.get_bootstrap_server(msk_arn=msk_arn)

        function = self.init_proxy_lambda(
            vpc=vpc,
            kafka_security_groud=kafka_security_group,
            bootstrap_broker=bootstrap_broker,
            msk_arn=msk_arn,
            topic_name=topic_name,
        )

        self.init_api_gateway(function, vpc, kafka_security_group)  # type: ignore

    def init_api_gateway(
        self,
        _function: f.IFunction,
        vpc: ec2.IVpc,
        kafka_security_groud: ec2.ISecurityGroup,
    ):
        """Creates the API Gateway endpoint

        Args:
            function (f.IFunction): Lambda backend funtion
        """
        vpc_endpoint = ec2.InterfaceVpcEndpoint(
            self,
            "apigatewayendpoint",
            service=ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,  # type: ignore
            vpc=vpc,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT),
            private_dns_enabled=True,
            security_groups=[kafka_security_groud],
        )

        rest_api_props = apig.RestApiProps(
            rest_api_name="kafka-events-api",
            deploy_options=apig.StageOptions(
                logging_level=apig.MethodLoggingLevel.INFO, data_trace_enabled=True
            ),
            default_method_options=apig.MethodOptions(
                authorization_type=apig.AuthorizationType.NONE
            ),
        )

        prod_alias = f.Alias(
            self, "prod-alias", alias_name="prod", version=_function.current_version
        )

        prod_alias.add_auto_scaling(min_capacity=20, max_capacity=60)

        rest_api = apig.RestApi(
            self,
            "messagesapiendpoint",
            rest_api_name="kafka-events-api",
            deploy_options=apig.StageOptions(
                logging_level=apig.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                tracing_enabled=True,
            ),
            default_method_options=apig.MethodOptions(
                authorization_type=apig.AuthorizationType.NONE
            ),
        )
        rest_api.root.add_method("POST", apig.LambdaIntegration(prod_alias))

    def init_proxy_lambda(
        self,
        vpc: ec2.IVpc,
        kafka_security_groud: ec2.ISecurityGroup,
        bootstrap_broker: str,
        msk_arn: str,
        topic_name: str,
    ):
        function = f.Function(
            self,
            "KafkaProducer",
            runtime=f.Runtime.JAVA_11,  # type: ignore
            handler="software.amazon.samples.kafka.lambda.SimpleApiGatewayKafkaProxy::handleRequest",
            timeout=Duration.seconds(LAMBDA_TIMEOUT_SECONDS),
            log_retention=logs.RetentionDays.ONE_DAY,
            code=self.build_mvn_package(),
            tracing=f.Tracing.ACTIVE,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
            ),
            security_groups=[kafka_security_groud],
            reserved_concurrent_executions=get_paramter(
                self.node, P_MAX_CONCURRENCY, 60
            ),
            environment={
                "bootstrap_server": bootstrap_broker,
                "JAVA_TOOL_OPTIONS": "-XX:+TieredCompilation -XX:TieredStopAtLevel=1",
                "POWERTOOLS_LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "KafkaProducer",
            },
            memory_size=1024,
        )
        

        access_kafka_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka-cluster:Connect",
            ],
            resources=[msk_arn],
        )

        admin_kafka_topics = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka-cluster:WriteData",
                "kafka-cluster:DescribeTopic",
            ],
            resources=[
                get_topic_name(kafka_cluster_arn=msk_arn, topic_name=topic_name)
            ],
        )

        access_to_user_groups = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["kafka-cluster:AlterGroup", "kafka-cluster:DescribeGroup"],
            resources=[get_group_name(kafka_cluster_arn=msk_arn, group_name="*")],
        )
        function.add_to_role_policy(access_kafka_policy)
        function.add_to_role_policy(admin_kafka_topics)
        function.add_to_role_policy(access_to_user_groups)

        return function

    def build_mvn_package(self):

        home = str(Path.home())

        log.info("Building Java Project using M2 home from")
        m2_home = os.path.join(home, ".m2/")
        log.info(f"M2_home={m2_home}")

        code = f.Code.from_asset(
            path=os.path.join("..", "api-gateway-lambda-proxy"),
            bundling=BundlingOptions(
                image=f.Runtime.JAVA_11.bundling_image,
                command=[
                    "/bin/sh",
                    "-c",
                    "mvn clean install -q && cp /asset-input/target/ApiGatewayLambdaProxy.zip /asset-output/",
                ],
                user="root",
                output_type=BundlingOutput.ARCHIVED,
                volumes=[DockerVolume(host_path=m2_home, container_path="/root/.m2/")],
            ),
        )
        return code

    def get_bootstrap_server(self, msk_arn: str):

        
        sdk_call = cs.AwsSdkCall(
            service="Kafka",
            action="getBootstrapBrokers",  # aws kafka get-bootstrap-brokers --cluster-arn {kafka_cluster_arn} --query "BootstrapBrokerStringSaslIam" --region {region})
            parameters={"ClusterArn": msk_arn},
            region=self.region,
            physical_resource_id=cs.PhysicalResourceId.of(
                f"csgetbootstrapbrokers{msk_arn}"
            ),
        )
        cs.PhysicalResourceId.of
        kafka_cli_call = cs.AwsCustomResource(
            self,
            "kafkaclicall",
            function_name=CUSTOM_RESOURCE_PHYISCAL_FUNCTION_NAME,
            on_create=sdk_call,
            log_retention=logs.RetentionDays.ONE_DAY,
            install_latest_aws_sdk=True,
            policy=cs.AwsCustomResourcePolicy.from_sdk_calls(
                resources=[msk_arn]
            ),
            timeout=Duration.minutes(2),
        )

        boot_strap_broker = kafka_cli_call.get_response_field(
            "BootstrapBrokerStringSaslIam"
        )

        log.info("Kafka bootstrap broker url %s", boot_strap_broker)

        return kafka_cli_call.get_response_field("BootstrapBrokerStringSaslIam")
