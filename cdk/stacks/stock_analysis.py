from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_logs as logs,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_certificatemanager as acm,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class StockAnalysisStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        ecr_repository_name: str,
        container_image: str,
        domain_name: str = None,
        certificate_arn: str = None,
        hosted_zone_id: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(self, "StockAnalysisVpc", max_azs=2, nat_gateways=1)

        # Create an ECS cluster
        cluster = ecs.Cluster(self, "StockAnalysisCluster", vpc=vpc, container_insights=True)

        # Create a reference to the existing ECR repository
        repository = ecr.Repository.from_repository_name(
            self, "StockAnalysisRepository", repository_name=ecr_repository_name
        )

        # Create a task execution role
        execution_role = iam.Role(
            self,
            "StockAnalysisTaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ],
        )

        # Create a task role
        task_role = iam.Role(self, "StockAnalysisTaskRole", assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"))

        # CloudWatch Logs for the container
        log_group = logs.LogGroup(
            self, "StockAnalysisLogGroup", retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY
        )

        # Task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "StockAnalysisTaskDefinition",
            memory_limit_mib=2048,
            cpu=1024,
            execution_role=execution_role,
            task_role=task_role,
        )

        # Add container to the task definition
        container = task_definition.add_container(
            "StockAnalysisContainer",
            image=ecs.ContainerImage.from_registry(container_image),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="stock-analysis", log_group=log_group),
            port_mappings=[
                ecs.PortMapping(
                    container_port=8501, host_port=8501, protocol=ecs.Protocol.TCP  # Streamlit default port
                )
            ],
            environment={
                # Add any environment variables your application needs
                "STREAMLIT_SERVER_PORT": "8501",
                "STREAMLIT_SERVER_HEADLESS": "true",
                "STREAMLIT_SERVER_ENABLE_CORS": "true",
            },
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    "curl -f http://localhost:8501/healthz || curl -f http://stock-tracker.joseph-moussa.com/healthz",
                ],
                interval=Duration.seconds(60),
                timeout=Duration.seconds(10),
                retries=3,
            ),
        )

        # Fargate service security group
        service_sg = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=vpc,
            description="Security group for Stock Analysis Fargate service",
            allow_all_outbound=True,
        )

        # Allow inbound from the load balancer
        service_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(8501), description="Allow inbound access to Streamlit"
        )

        # Fargate service
        service = ecs.FargateService(
            self,
            "StockAnalysisService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            assign_public_ip=False,
            security_groups=[service_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        # Application Load Balancer
        lb = elbv2.ApplicationLoadBalancer(self, "StockAnalysisLB", vpc=vpc, internet_facing=True)

        # Create target group with explicit protocol
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "StockAnalysisTargetGroup",
            port=8501,
            protocol=elbv2.ApplicationProtocol.HTTP,  # Explicitly define HTTP protocol
            vpc=vpc,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/healthz", port="8501", interval=Duration.seconds(60), timeout=Duration.seconds(30)
            ),
        )

        # Add targets to the target group
        target_group.add_target(service)

        # Add HTTPS listener if domain name and certificate are provided
        if domain_name and hosted_zone_id:
            # Import certificate
            # certificate = acm.Certificate.from_certificate_arn(self, "Certificate", certificate_arn=certificate_arn)

            # DNS Record
            hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
                self, "HostedZone", hosted_zone_id=hosted_zone_id, zone_name=domain_name
            )

            # Create an ACM certificate
            certificate = acm.Certificate(
                self,
                "StockAnalysisCertificate",
                domain_name=domain_name,
                validation=acm.CertificateValidation.from_dns(hosted_zone),
            )

            # HTTPS Listener
            https_listener = lb.add_listener(
                "HttpsListener",
                port=443,
                certificates=[certificate],
                ssl_policy=elbv2.SslPolicy.RECOMMENDED,
                default_target_groups=[target_group],  # Use our target group with explicit protocol
            )

            # Redirect HTTP to HTTPS
            lb.add_redirect(
                source_port=80,
                source_protocol=elbv2.ApplicationProtocol.HTTP,
                target_port=443,
                target_protocol=elbv2.ApplicationProtocol.HTTPS,
            )

            route53.ARecord(
                self,
                "StockAnalysisDNS",
                zone=hosted_zone,
                record_name=domain_name,
                target=route53.RecordTarget.from_alias(route53_targets.LoadBalancerTarget(lb)),
            )

            # Output the HTTPS endpoint
            CfnOutput(
                self,
                "StockAnalysisEndpointHTTPS",
                value=f"https://{domain_name}",
                description="Stock Analysis application HTTPS endpoint",
            )

        else:
            # HTTP Listener only
            http_listener = lb.add_listener(
                "HttpListener",
                port=80,
                default_target_groups=[target_group],  # Use our target group with explicit protocol
            )

            # Output the HTTP endpoint
            CfnOutput(
                self,
                "StockAnalysisEndpointHTTP",
                value=f"http://{lb.load_balancer_dns_name}",
                description="Stock Analysis application HTTP endpoint",
            )

        # Autoscaling for the service
        scaling = service.auto_scale_task_count(min_capacity=1, max_capacity=5)

        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(60),
        )

        # Output the CloudWatch Logs URL
        region = Stack.of(self).region
        CfnOutput(
            self,
            "StockAnalysisLogGroupURL",
            value=f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups/log-group/{log_group.log_group_name}",
            description="Stock Analysis CloudWatch log group",
        )
