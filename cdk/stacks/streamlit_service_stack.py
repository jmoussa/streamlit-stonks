from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
)
import aws_cdk as core


class StreamlitServiceStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Configuration parameters (can be passed from context or environment)
        ecr_repository_name = self.node.try_get_context("ecr_repository_name") or "streamlit-service"
        container_port = int(self.node.try_get_context("container_port") or 8501)  # Default Streamlit port
        cpu = int(self.node.try_get_context("cpu") or 512)
        memory_limit_mib = int(self.node.try_get_context("memory_limit_mib") or 1024)
        desired_count = int(self.node.try_get_context("desired_count") or 2)
        health_check_path = self.node.try_get_context("health_check_path") or "/_stcore/health"

        # Create VPC
        vpc = ec2.Vpc(
            self,
            "StreamlitVpc",
            max_azs=2,  # Use 2 Availability Zones for high availability
            nat_gateways=1,  # Add NAT Gateway for private subnets
        )

        # Create ECS Cluster
        cluster = ecs.Cluster(self, "StreamlitCluster", vpc=vpc)

        # Get reference to existing ECR Repository
        repository = ecr.Repository.from_repository_name(
            self, "StreamlitRepository", repository_name=ecr_repository_name
        )

        # Create Fargate Service with Load Balancer
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "StreamlitService",
            cluster=cluster,
            cpu=cpu,
            memory_limit_mib=memory_limit_mib,
            desired_count=desired_count,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(repository),
                container_port=container_port,
                enable_logging=True,
            ),
            public_load_balancer=True,
        )

        # Configure health check for the target group
        fargate_service.target_group.configure_health_check(
            path=health_check_path,
            port=str(container_port),
            healthy_http_codes="200",
            interval=cdk.Duration.seconds(60),
            timeout=cdk.Duration.seconds(30),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        # Allow the Fargate task to pull images from ECR
        repository.grant_pull(fargate_service.task_definition.execution_role)

        # Add autoscaling
        scaling = fargate_service.service.auto_scale_task_count(max_capacity=10, min_capacity=1)

        # Add scaling based on CPU utilization
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=cdk.Duration.seconds(60),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )

        # Output the load balancer DNS name
        cdk.CfnOutput(
            self,
            "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name,
            description="The DNS name of the load balancer",
        )
