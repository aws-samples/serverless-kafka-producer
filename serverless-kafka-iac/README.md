
# Welcome to your CDK Python project!

This is cdk application deploying a demo infrastructure as depicted in that blog entry:

This example walks you through how to build a serverless real-time stream
producer application using Amazon API Gateway and AWS Lambda.
For testing, this blog includes a sample AWS Cloud Development Kit (CDK)
application. This creates a demo environment including an Amazon Managed
Streaming for Apache Kafka (MSK) cluster and a bastion host for observing the
produced messages on the cluster.
You deploy a serverless Kafka producer to Lambda that forwards API Gateway
calls to a Kafka topic (on an Amazon Managed Streaming for Apache Kafka
(MSK) cluster). The API Gateway calls are sent via Amazon Kinesis data stream,
which acts as a control plane, to control throughput, latency and concurrency.

![image info](./img/Architecture.drawio.png)

This repository will contains the cdk code required to deploy the application.

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

Install cdk requirements
```
$ pip3 install -r requirements.txt
```

Bootstrap your account for CDK usage
```
$ cdk bootstrap aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION
```
Run cdk synth to build code and test requirements
```
$ cdk synth
```
Run ‘cdk deploy’ to deploy the code to your AWS account
```
$ cdk deploy
```

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
