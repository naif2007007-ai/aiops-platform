#!/bin/bash
# ============================================================
# deploy.sh — Build Docker image, push to ECR, deploy to
#             AWS App Runner.
#
# Prerequisites:
#   - AWS CLI configured with sufficient permissions
#   - Docker daemon running (Cloud9 / EC2 with Docker)
#   - Set the three variables below before running
#
# Usage:
#   chmod +x deploy.sh && ./deploy.sh
# ============================================================

set -e

# ── CONFIGURE THESE ──────────────────────────────────────────
AWS_ACCOUNT_ID="123456789012"          # your AWS account ID
AWS_REGION="us-east-1"
ECR_REPO="aiops-dashboard"
APP_RUNNER_SERVICE="aiops-platform"
S3_BUCKET="aiops-platform-poc"
# ─────────────────────────────────────────────────────────────

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_URI}/${ECR_REPO}:latest"

echo "╔══════════════════════════════════════════════╗"
echo "  AI-Ops Platform — Cloud Deployment"
echo "╚══════════════════════════════════════════════╝"

# 1. Create S3 bucket (idempotent)
echo "[1/6] Ensuring S3 bucket exists …"
aws s3api create-bucket \
  --bucket "${S3_BUCKET}" \
  --region "${AWS_REGION}" \
  --create-bucket-configuration LocationConstraint="${AWS_REGION}" \
  2>/dev/null || true
echo "  ✅ s3://${S3_BUCKET}"

# 2. Create ECR repository (idempotent)
echo "[2/6] Ensuring ECR repository exists …"
aws ecr create-repository \
  --repository-name "${ECR_REPO}" \
  --region "${AWS_REGION}" \
  2>/dev/null || true
echo "  ✅ ${ECR_URI}/${ECR_REPO}"

# 3. Authenticate Docker with ECR
echo "[3/6] Authenticating Docker with ECR …"
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${ECR_URI}"

# 4. Build Docker image from project root
echo "[4/6] Building Docker image …"
cd "$(dirname "$0")/../.."   # project root
docker build -t "${ECR_REPO}:latest" -f deployment/docker/Dockerfile .
docker tag "${ECR_REPO}:latest" "${IMAGE_URI}"

# 5. Push to ECR
echo "[5/6] Pushing to ECR …"
docker push "${IMAGE_URI}"
echo "  ✅ ${IMAGE_URI}"

# 6. Create / update App Runner service
echo "[6/6] Deploying to AWS App Runner …"

# Check if service already exists
EXISTING=$(aws apprunner list-services \
  --region "${AWS_REGION}" \
  --query "ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE}'].ServiceArn" \
  --output text 2>/dev/null)

if [ -z "$EXISTING" ]; then
  echo "  Creating new App Runner service …"
  SERVICE_ARN=$(aws apprunner create-service \
    --region "${AWS_REGION}" \
    --service-name "${APP_RUNNER_SERVICE}" \
    --source-configuration "{
      \"ImageRepository\": {
        \"ImageIdentifier\": \"${IMAGE_URI}\",
        \"ImageRepositoryType\": \"ECR\",
        \"ImageConfiguration\": {
          \"Port\": \"8080\",
          \"RuntimeEnvironmentVariables\": {
            \"AIOPS_S3_BUCKET\": \"${S3_BUCKET}\",
            \"AWS_DEFAULT_REGION\": \"${AWS_REGION}\"
          }
        }
      },
      \"AutoDeploymentsEnabled\": true
    }" \
    --instance-configuration '{"Cpu":"1 vCPU","Memory":"2 GB"}' \
    --query "Service.ServiceArn" --output text)
else
  echo "  Updating existing service …"
  SERVICE_ARN=$EXISTING
  aws apprunner start-deployment \
    --region "${AWS_REGION}" \
    --service-arn "${SERVICE_ARN}"
fi

# Wait for deployment
echo "  Waiting for service to become RUNNING …"
aws apprunner wait service-running \
  --region "${AWS_REGION}" \
  --service-arn "${SERVICE_ARN}" 2>/dev/null || true

# Print the public URL
PUBLIC_URL=$(aws apprunner describe-service \
  --region "${AWS_REGION}" \
  --service-arn "${SERVICE_ARN}" \
  --query "Service.ServiceUrl" --output text)

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "  ✅  Deployment complete!"
echo "  🌐  Dashboard URL: https://${PUBLIC_URL}"
echo "╚══════════════════════════════════════════════╝"
