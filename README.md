# Stock Analysis Dashboard

![GitHub Actions Workflow Status](https://github.com/yourusername/stock-analysis-app/actions/workflows/deploy.yml/badge.svg)

An interactive stock analysis dashboard built with Streamlit and deployed to AWS Fargate using AWS CDK and GitHub Actions.

## 📊 Features

- Interactive stock data visualization with Altair charts
- MACD (Moving Average Convergence Divergence) analysis
- Custom moving averages (10, 30, and 60 day)
- Multiple stock ticker support
- Responsive design for desktop and mobile

## 🚀 Deployment Architecture

This application is deployed on AWS with the following components:

- **AWS Fargate**: Runs the application container without managing servers
- **Application Load Balancer**: Routes traffic to the application
- **Amazon ECR**: Stores the Docker container images
- **AWS CloudWatch**: Monitors application logs and metrics
- **Auto Scaling**: Adjusts capacity based on demand
- **Route53 & ACM** (optional): Custom domain and HTTPS support

## 📁 Project Structure

```
stock-analysis-app/
├── app.py                     # Main Streamlit application
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker container definition
├── .github/                   # GitHub configuration
│   └── workflows/             # GitHub Actions workflows
│       └── deploy.yml         # CI/CD pipeline
├── cdk/                       # AWS CDK infrastructure code
│   ├── app.py                 # CDK application entry point
│   ├── requirements-cdk.txt   # CDK requirements
│   └── stock_analysis/        # CDK stack implementation
└── tests/                     # Test directory
```

## 🛠️ Local Development

### Prerequisites

- Python 3.10+
- Docker
- AWS CLI (for deployment)
- AWS CDK (for deployment)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/stock-analysis-app.git
   cd stock-analysis-app
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application locally:
   ```bash
   streamlit run app.py
   ```

5. Access the application at http://localhost:8501

### Docker Build

To build and run the Docker container locally:

```bash
docker build -t stock-analysis-app .
docker run -p 8501:8501 stock-analysis-app
```

## 🚢 Deployment

### Prerequisites

1. AWS account
2. GitHub repository with the code
3. GitHub Actions secrets configured (see below)

### GitHub Actions Secrets

Configure the following secrets in your GitHub repository:

- `AWS_ACCESS_KEY_ID`: AWS IAM access key
- `AWS_SECRET_ACCESS_KEY`: AWS IAM secret key
- `AWS_ACCOUNT_ID`: Your AWS account ID
- `DOMAIN_NAME` (optional): Your custom domain
- `CERTIFICATE_ARN` (optional): ACM certificate ARN
- `HOSTED_ZONE_ID` (optional): Route53 hosted zone ID

### Manual Deployment

1. Push to the main branch to trigger automatic deployment through GitHub Actions:
   ```bash
   git push origin main
   ```

2. Monitor the deployment in the GitHub Actions tab of your repository.

3. For manual deployment, navigate to the Actions tab and run the "Build and Deploy Stock Analysis App" workflow.

## 📝 License

[MIT License](LICENSE)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit an Issue/Pull Request.