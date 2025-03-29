#!/usr/bin/env python3
import os
from aws_cdk import App, Environment

from stacks.stock_analysis_stack import StockAnalysisStack

app = App()

# Environment variables can be passed from the CI/CD pipeline
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
ecr_repository_name = os.environ.get("ECR_REPOSITORY_NAME", "stock-analysis-app")
container_image = os.environ.get("CONTAINER_IMAGE")  # Format: {account}.dkr.ecr.{region}.amazonaws.com/{repo}:{tag}
domain_name = os.environ.get("DOMAIN_NAME", "")  # Optional: example.com
certificate_arn = os.environ.get("CERTIFICATE_ARN", "")  # Optional: arn:aws:acm:{region}:{account}:certificate/{id}
hosted_zone_id = os.environ.get("HOSTED_ZONE_ID", "")  # Optional: Route53 hosted zone ID

# Create the stack
StockAnalysisStack(
    app,
    "StockAnalysisStack",
    env=Environment(account=account, region=region),
    ecr_repository_name=ecr_repository_name,
    container_image=container_image,
    domain_name=domain_name,
    certificate_arn=certificate_arn,
    hosted_zone_id=hosted_zone_id,
)

app.synth()
