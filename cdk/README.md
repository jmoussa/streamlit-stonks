# GitHub Actions Secrets for Stock Analysis App Deployment

The following secrets need to be configured in your GitHub repository:

## Required Secrets

| Secret Name | Description |
|-------------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key with permissions for ECR, ECS, CDK deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key |
| `AWS_ACCOUNT_ID` | Your AWS account ID |

## Optional Secrets (for custom domain and HTTPS)

| Secret Name | Description |
|-------------|-------------|
| `DOMAIN_NAME` | Your custom domain name (e.g., stockapp.example.com) |
| `CERTIFICATE_ARN` | ARN of AWS Certificate Manager certificate for HTTPS |
| `HOSTED_ZONE_ID` | Route53 hosted zone ID |

## How to Set Up Secrets

1. Go to your GitHub repository
2. Navigate to Settings > Secrets and variables > Actions
3. Click on "New repository secret"
4. Add each of the secrets listed above

## Required IAM Permissions

The AWS IAM user associated with the access keys should have the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage",
                "ecr:CreateRepository",
                "ecr:DescribeRepositories",
                "ecr:ListImages",
                "ecr:DeleteRepository",
                "ecr:BatchDeleteImage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "ecs:*",
                "ec2:*",
                "elasticloadbalancing:*",
                "iam:*",
                "logs:*",
                "route53:*",
                "acm:*"
            ],
            "Resource": "*"
        }
    ]
}
```

Note: In a production environment, it's recommended to scope down these permissions to only the specific resources needed.