#!/usr/bin/env python3
from aws_cdk import App, Environment
import aws_cdk as cdk
import os
from stacks.streamlit_service_stack import StreamlitServiceStack
from stacks.ecr import ECRRepositoryStack
import argparse as ap

parser = ap.ArgumentParser()
parser.add_argument("--stack", type=str, default="streamlit-service-stack")
args = parser.parse_args()

app = App()

# Environment variables can be passed from the CI/CD pipeline
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
ecr_repository_name = os.environ.get("ECR_REPOSITORY_NAME", "streamlit-service")
container_image = os.environ.get("CONTAINER_IMAGE")  # Format: {account}.dkr.ecr.{region}.amazonaws.com/{repo}:{tag}
domain_name = os.environ.get("DOMAIN_NAME", "")  # Optional: example.com
certificate_arn = os.environ.get("CERTIFICATE_ARN", "")  # Optional: arn:aws:acm:{region}:{account}:certificate/{id}
hosted_zone_id = os.environ.get("HOSTED_ZONE_ID", "")  # Optional: Route53 hosted zone ID

if args.stack == "ecr-stack":
    ECRRepositoryStack(
        app,
        "ecr-stack",
        ecr_repository_name=ecr_repository_name,
        env=Environment(account=account, region=region),
    )

if args.stack == "streamlit-service-stack":
    StreamlitServiceStack(
        app,
        "streamlit-service-stack",
        env=cdk.Environment(
            account=app.node.try_get_context("account") or account,
            region=app.node.try_get_context("region") or region,
        ),
    )

app.synth()
