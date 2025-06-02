
#!/bin/bash

# EKS 배포 스크립트
set -e

# 환경 변수 설정
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-"your-account-id"}
AWS_REGION=${AWS_REGION:-"ap-northeast-2"}
ECR_REPOSITORY=${ECR_REPOSITORY:-"eks-assistant"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
CLUSTER_NAME=${CLUSTER_NAME:-"your-eks-cluster"}

echo "=== EKS Assistant 배포 시작 ==="

# 1. ECR 리포지토리 생성 (이미 존재하는 경우 스킵)
echo "ECR 리포지토리 확인/생성 중..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# 2. Docker 로그인
echo "ECR에 Docker 로그인 중..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 3. Docker 이미지 빌드
echo "Docker 이미지 빌드 중..."
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

# 4. Docker 이미지 태그 및 푸시
echo "Docker 이미지 푸시 중..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# 5. kubectl 컨텍스트 업데이트
echo "EKS 클러스터 컨텍스트 업데이트 중..."
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME

# 6. Kubernetes 매니페스트 업데이트
echo "Kubernetes 매니페스트 업데이트 중..."
sed -i "s|your-account.dkr.ecr.region.amazonaws.com|$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com|g" k8s-deployment.yaml
sed -i "s|YOUR-ACCOUNT-ID|$AWS_ACCOUNT_ID|g" k8s-deployment.yaml

# 7. Kubernetes에 배포
echo "Kubernetes에 배포 중..."
kubectl apply -f k8s-deployment.yaml

# 8. 배포 상태 확인
echo "배포 상태 확인 중..."
kubectl rollout status deployment/eks-assistant-app

# 9. 서비스 URL 확인
echo "서비스 URL 확인 중..."
echo "다음 명령으로 LoadBalancer URL을 확인하세요:"
echo "kubectl get service eks-assistant-service"

echo "=== EKS Assistant 배포 완료 ==="
