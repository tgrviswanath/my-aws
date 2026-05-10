# Level 2 — Intermediate Hands-On Scenarios

> **Goal**: Build real application infrastructure.  
> **Prerequisites**: Completed Level 1, Docker installed, Terraform installed.

---

## Scenario 6 — Build Custom VPC Architecture

**Skills**: VPC, Networking, Routing  
**Time**: 45 minutes  
**Cost**: ~$0.05 (NAT Gateway)

### Architecture
```
Internet
    ↓
Internet Gateway
    ↓
Public Subnet (10.0.1.0/24)
    ├── EC2 (web server)
    └── NAT Gateway
            ↓
Private Subnet (10.0.2.0/24)
    └── RDS (database)
```

### Step-by-Step

```bash
REGION="us-east-1"

# Step 1: Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-custom-vpc}]' \
  --query 'Vpc.VpcId' --output text)

aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
echo "VPC: $VPC_ID"

# Step 2: Create subnets
PUBLIC_SUBNET=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone ${REGION}a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet}]' \
  --query 'Subnet.SubnetId' --output text)

PRIVATE_SUBNET=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone ${REGION}b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-subnet}]' \
  --query 'Subnet.SubnetId' --output text)

# Enable auto-assign public IP for public subnet
aws ec2 modify-subnet-attribute \
  --subnet-id $PUBLIC_SUBNET \
  --map-public-ip-on-launch

echo "Public subnet: $PUBLIC_SUBNET"
echo "Private subnet: $PRIVATE_SUBNET"

# Step 3: Internet Gateway (for public subnet)
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=my-igw}]' \
  --query 'InternetGateway.InternetGatewayId' --output text)

aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

echo "Internet Gateway: $IGW_ID"

# Step 4: Public route table (routes to IGW)
PUBLIC_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=public-rt}]' \
  --query 'RouteTable.RouteTableId' --output text)

aws ec2 create-route \
  --route-table-id $PUBLIC_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

aws ec2 associate-route-table \
  --route-table-id $PUBLIC_RT \
  --subnet-id $PUBLIC_SUBNET

# Step 5: NAT Gateway (for private subnet internet access)
EIP_ALLOC=$(aws ec2 allocate-address \
  --domain vpc \
  --query 'AllocationId' --output text)

NAT_GW=$(aws ec2 create-nat-gateway \
  --subnet-id $PUBLIC_SUBNET \
  --allocation-id $EIP_ALLOC \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=my-nat}]' \
  --query 'NatGateway.NatGatewayId' --output text)

echo "Waiting for NAT Gateway..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW

# Step 6: Private route table (routes to NAT)
PRIVATE_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=private-rt}]' \
  --query 'RouteTable.RouteTableId' --output text)

aws ec2 create-route \
  --route-table-id $PRIVATE_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW

aws ec2 associate-route-table \
  --route-table-id $PRIVATE_RT \
  --subnet-id $PRIVATE_SUBNET

# Step 7: Security groups
SG_WEB=$(aws ec2 create-security-group \
  --group-name "web-sg" --description "Web server" \
  --vpc-id $VPC_ID --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress --group-id $SG_WEB --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_WEB --protocol tcp --port 22 --cidr 0.0.0.0/0

SG_DB=$(aws ec2 create-security-group \
  --group-name "db-sg" --description "Database" \
  --vpc-id $VPC_ID --query 'GroupId' --output text)

# DB only accessible from web servers
aws ec2 authorize-security-group-ingress \
  --group-id $SG_DB --protocol tcp --port 3306 \
  --source-group $SG_WEB

echo ""
echo "✅ Custom VPC created!"
echo "VPC: $VPC_ID"
echo "Public subnet: $PUBLIC_SUBNET"
echo "Private subnet: $PRIVATE_SUBNET"
echo ""
echo "Architecture:"
echo "  Internet → IGW → Public Subnet (EC2) → NAT → Private Subnet (RDS)"
```

### What You Learned
- ✅ VPC, subnets, route tables
- ✅ Internet Gateway vs NAT Gateway
- ✅ Security group chaining (DB only from web)
- ✅ Public vs private subnet design

---

## Scenario 7 — Deploy Full-Stack App on EC2

**Skills**: EC2, Linux, Nginx, PM2, Node.js  
**Time**: 60 minutes

### Architecture
```
Internet → EC2 (public IP)
              ├── Nginx (port 80) → React build files
              └── Nginx proxy → Node.js API (port 3000)
                                      ↓
                                   MySQL (RDS)
```

### Step-by-Step

```bash
# Launch EC2 in public subnet from Scenario 6
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.small \
  --key-name my-ec2-key \
  --security-group-ids $SG_WEB \
  --subnet-id $PUBLIC_SUBNET \
  --user-data '#!/bin/bash
    # Install Node.js
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    yum install -y nodejs nginx git

    # Install PM2 (process manager)
    npm install -g pm2

    # Start Nginx
    systemctl start nginx
    systemctl enable nginx' \
  --query 'Instances[0].InstanceId' --output text)

aws ec2 wait instance-running --instance-ids $INSTANCE_ID
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "Server IP: $PUBLIC_IP"
```

```bash
# SSH into server
ssh -i my-ec2-key.pem ec2-user@$PUBLIC_IP

# ── On the server ─────────────────────────────────────────────────────────────

# Create a simple Node.js API
mkdir -p /app/api && cd /app/api

cat > server.js << 'EOF'
const http = require('http');
const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.url === '/api/health') {
    res.end(JSON.stringify({ status: 'healthy', server: require('os').hostname() }));
  } else if (req.url === '/api/users') {
    res.end(JSON.stringify([
      { id: 1, name: 'Alice' },
      { id: 2, name: 'Bob' }
    ]));
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});
server.listen(3000, () => console.log('API running on port 3000'));
EOF

# Start with PM2 (keeps running after SSH disconnect)
pm2 start server.js --name "api"
pm2 startup  # Auto-start on reboot
pm2 save

# Create React frontend (simple HTML simulating React build)
mkdir -p /var/www/html
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head><title>Full Stack App</title></head>
<body>
  <h1>Full Stack App on EC2</h1>
  <div id="users"></div>
  <script>
    fetch('/api/users')
      .then(r => r.json())
      .then(users => {
        document.getElementById('users').innerHTML =
          users.map(u => `<p>${u.id}: ${u.name}</p>`).join('');
      });
  </script>
</body>
</html>
EOF

# Configure Nginx as reverse proxy
cat > /etc/nginx/conf.d/app.conf << 'EOF'
server {
    listen 80;
    server_name _;

    # Serve frontend
    location / {
        root /var/www/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to Node.js
    location /api/ {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

nginx -t && systemctl reload nginx

echo "✅ App deployed!"
echo "Frontend: http://$PUBLIC_IP"
echo "API: http://$PUBLIC_IP/api/health"
```

### What You Learned
- ✅ Full-stack deployment on EC2
- ✅ Nginx as reverse proxy
- ✅ PM2 for Node.js process management
- ✅ Production server configuration

---

## Scenario 8 — Dockerize Full Application

**Skills**: Docker, Docker Compose  
**Time**: 45 minutes

### Step-by-Step

```bash
# Create project structure
mkdir -p fullstack-docker/{frontend,backend}
cd fullstack-docker
```

```dockerfile
# backend/Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```yaml
# docker-compose.yml
version: "3.9"

services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "3000:3000"
    environment:
      - DB_HOST=database
      - DB_USER=root
      - DB_PASSWORD=password
      - DB_NAME=myapp
    depends_on:
      database:
        condition: service_healthy

  database:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: myapp
    volumes:
      - db_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  db_data:
```

```bash
# Build and run
docker-compose up -d --build

# Check status
docker-compose ps
docker-compose logs -f backend

# Test
curl http://localhost/api/health

# Stop
docker-compose down
```

### What You Learned
- ✅ Multi-container applications
- ✅ Docker Compose for local development
- ✅ Service dependencies and health checks
- ✅ Volume persistence for databases

---

## Scenario 9 — Push Docker Images to ECR

**Skills**: Docker, ECR  
**Time**: 20 minutes

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Step 1: Create ECR repositories
for REPO in frontend backend; do
  aws ecr create-repository \
    --repository-name "myapp-${REPO}" \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability IMMUTABLE \
    --region $REGION
  echo "Created: myapp-${REPO}"
done

# Step 2: Authenticate Docker
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ECR_URI

# Step 3: Build, tag, push
VERSION="v1.0.0"

for SERVICE in frontend backend; do
  echo "Building $SERVICE..."
  docker build -t myapp-${SERVICE}:${VERSION} ./${SERVICE}/
  docker tag myapp-${SERVICE}:${VERSION} ${ECR_URI}/myapp-${SERVICE}:${VERSION}
  docker push ${ECR_URI}/myapp-${SERVICE}:${VERSION}
  echo "✅ Pushed: ${ECR_URI}/myapp-${SERVICE}:${VERSION}"
done

# Step 4: Verify
aws ecr describe-images \
  --repository-name myapp-frontend \
  --query 'imageDetails[*].{Tag:imageTags[0],Size:imageSizeInBytes}' \
  --output table
```

### What You Learned
- ✅ ECR repository management
- ✅ Docker authentication with ECR
- ✅ Image tagging strategy (immutable tags)
- ✅ Image scanning for vulnerabilities

---

## Scenario 10 — Deploy Containers to ECS Fargate

**Skills**: ECS, Fargate, Load Balancer  
**Time**: 30 minutes

```bash
# Step 1: Create ECS cluster
aws ecs create-cluster \
  --cluster-name "myapp-cluster" \
  --capacity-providers FARGATE FARGATE_SPOT

# Step 2: Register task definition
aws ecs register-task-definition \
  --family "myapp-backend" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 256 --memory 512 \
  --execution-role-arn arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole \
  --container-definitions "[{
    \"name\": \"backend\",
    \"image\": \"${ECR_URI}/myapp-backend:v1.0.0\",
    \"portMappings\": [{\"containerPort\": 3000}],
    \"logConfiguration\": {
      \"logDriver\": \"awslogs\",
      \"options\": {
        \"awslogs-group\": \"/ecs/myapp-backend\",
        \"awslogs-region\": \"${REGION}\",
        \"awslogs-stream-prefix\": \"ecs\"
      }
    }
  }]"

# Step 3: Create ECS service
aws ecs create-service \
  --cluster "myapp-cluster" \
  --service-name "backend-service" \
  --task-definition "myapp-backend:1" \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "{
    \"awsvpcConfiguration\": {
      \"subnets\": [\"${PRIVATE_SUBNET}\"],
      \"securityGroups\": [\"${SG_WEB}\"],
      \"assignPublicIp\": \"DISABLED\"
    }
  }"

# Step 4: Check deployment
aws ecs describe-services \
  --cluster myapp-cluster \
  --services backend-service \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

### What You Learned
- ✅ ECS cluster and task definitions
- ✅ Fargate (serverless containers)
- ✅ Service deployment and scaling
- ✅ Container logging to CloudWatch

---

## Scenario 11 — Terraform AWS Infrastructure

**Skills**: Terraform, IaC  
**Time**: 45 minutes

```hcl
# main.tf — Complete VPC + EC2 + Security Groups

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.region
}

variable "region"        { default = "us-east-1" }
variable "instance_type" { default = "t3.micro" }

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "terraform-vpc" }
}

# Public subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags = { Name = "public-subnet" }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "main-igw" }
}

# Route table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Security group
resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = aws_vpc.main.id

  ingress { from_port = 80;  to_port = 80;  protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 22;  to_port = 22;  protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0;   to_port = 0;   protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "web-sg" }
}

# EC2 instance
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter { name = "name"; values = ["al2023-ami-*-x86_64"] }
}

resource "aws_instance" "web" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]

  user_data = <<-EOF
    #!/bin/bash
    yum install -y nginx
    systemctl start nginx
    echo "<h1>Deployed by Terraform!</h1>" > /usr/share/nginx/html/index.html
  EOF

  tags = { Name = "terraform-web-server" }
}

output "public_ip"  { value = aws_instance.web.public_ip }
output "website_url" { value = "http://${aws_instance.web.public_ip}" }
```

```bash
# Deploy
terraform init
terraform plan
terraform apply -auto-approve

# Get outputs
terraform output

# Destroy when done
terraform destroy -auto-approve
```

### What You Learned
- ✅ Terraform providers, resources, variables, outputs
- ✅ Infrastructure as Code principles
- ✅ Reproducible deployments
- ✅ Plan before apply (preview changes)

---

## Scenario 12 — CI/CD Pipeline with GitHub Actions

**Skills**: GitHub Actions, ECR, ECS  
**Time**: 45 minutes

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy to AWS

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: myapp-backend
  ECS_CLUSTER: myapp-cluster
  ECS_SERVICE: backend-service
  CONTAINER_NAME: backend

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Run tests
        run: |
          npm ci
          npm test

      - name: Build, tag, and push image to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --force-new-deployment

      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster $ECS_CLUSTER \
            --services $ECS_SERVICE
          echo "✅ Deployment complete!"
```

```bash
# Setup GitHub secrets:
# AWS_ACCESS_KEY_ID     → IAM user access key
# AWS_SECRET_ACCESS_KEY → IAM user secret key

# Push to main branch to trigger pipeline
git add .
git commit -m "feat: add CI/CD pipeline"
git push origin main

# Watch pipeline in GitHub Actions tab
```

### What You Learned
- ✅ GitHub Actions workflow syntax
- ✅ AWS credentials in CI/CD
- ✅ Automated build → push → deploy
- ✅ Deployment verification

---

## Summary — Intermediate Level Complete ✅

| Scenario | Services | Key Concept |
|---------|---------|------------|
| 6 | VPC | Custom network, subnets, routing |
| 7 | EC2, Nginx | Full-stack deployment |
| 8 | Docker | Containerization, Compose |
| 9 | ECR | Container registry |
| 10 | ECS, Fargate | Container orchestration |
| 11 | Terraform | Infrastructure as Code |
| 12 | GitHub Actions | CI/CD automation |

**Next**: Move to `19_scenarios_advanced.md` → Auto Scaling, Serverless API, Monitoring, Event-driven.
