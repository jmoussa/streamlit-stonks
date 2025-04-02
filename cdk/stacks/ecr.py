import aws_cdk as cdk
from aws_cdk import aws_ecr as ecr


class ECRRepositoryStack(cdk.Stack):
    def __init__(self, scope, id: str, ecr_repository_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.repository = ecr.Repository(
            self,
            "Repository",
            repository_name=ecr_repository_name,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        output_1 = cdk.CfnOutput(
            self,
            "RepositoryUri",
            value=self.repository.repository_uri,
            description="ECR Repository URI",
        )

        output_2 = cdk.CfnOutput(
            self,
            "RepositoryName",
            value=self.repository.repository_name,
            description="ECR Repository Name",
        )
