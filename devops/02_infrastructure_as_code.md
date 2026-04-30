# Infrastructure as Code — CloudFormation & Terraform

## Why IaC?

```
Manual console clicks:
❌ Not reproducible
❌ No version control
❌ Drift between environments
❌ Hard to audit

IaC:
✅ Reproducible environments
✅ Version controlled
✅ Consistent dev/staging/prod
✅ Auditable changes
✅ Automated provisioning
```

---

## AWS CloudFormation

CloudFormation is AWS-native IaC. Declarative JSON/YAML templates.

### Template Structure

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: My application stack

Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      - Label: {default: "Network Configuration"}
        Parameters: [VpcId, SubnetIds]

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, production]
    Default: dev
  InstanceType:
    Type: String
    Default: t3.micro
  VpcId:
    Type: AWS::EC2::VPC::Id

Mappings:
  EnvironmentConfig:
    dev:
      InstanceCount: 1
      InstanceType: t3.micro
    production:
      InstanceCount: 4
      InstanceType: m5.large

Conditions:
  IsProduction: !Equals [!Ref Environment, production]
  IsNotProduction: !Not [!Condition IsProduction]

Resources:
  # ... your resources

Outputs:
  LoadBalancerDNS:
    Description: ALB DNS name
    Value: !GetAtt ALB.DNSName
    Export:
      Name: !Sub "${AWS::StackName}-ALB-DNS"
```

### Intrinsic Functions

```yaml
# Reference parameter or resource
!Ref MyParameter
!Ref MyResource  # Returns resource ID

# Get attribute
!GetAtt MyALB.DNSName
!GetAtt MyLambda.Arn

# Substitution
!Sub "arn:aws:s3:::${BucketName}/*"
!Sub "${AWS::AccountId}-${AWS::Region}-data"

# Join
!Join ["-", [!Ref AWS::StackName, "bucket"]]

# Select from list
!Select [0, !GetAZs '']  # First AZ

# If condition
!If [IsProduction, m5.large, t3.micro]

# Import from another stack
!ImportValue "network-stack-VpcId"

# Base64 encode
Fn::Base64: |
  #!/bin/bash
  yum update -y
```

### Complete 3-Tier App Stack

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 3-tier web application

Parameters:
  Environment:
    Type: String
    Default: production
  DBPassword:
    Type: String
    NoEcho: true

Resources:
  # ── VPC ──────────────────────────────────────────────────────────────────
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: true

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.11.0/24
      AvailabilityZone: !Select [0, !GetAZs '']

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.12.0/24
      AvailabilityZone: !Select [1, !GetAZs '']

  # ── Security Groups ───────────────────────────────────────────────────────
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: ALB security group
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0

  AppSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: App server security group
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8080
          ToPort: 8080
          SourceSecurityGroupId: !Ref ALBSecurityGroup

  DBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Database security group
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref AppSecurityGroup

  # ── Load Balancer ─────────────────────────────────────────────────────────
  ALB:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Scheme: internet-facing
      Subnets: [!Ref PublicSubnet1, !Ref PublicSubnet2]
      SecurityGroups: [!Ref ALBSecurityGroup]

  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Protocol: HTTP
      Port: 8080
      VpcId: !Ref VPC
      HealthCheckPath: /health
      TargetType: instance

  # ── Auto Scaling ──────────────────────────────────────────────────────────
  LaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateData:
        ImageId: ami-0c02fb55956c7d316
        InstanceType: t3.medium
        SecurityGroupIds: [!Ref AppSecurityGroup]
        IamInstanceProfile:
          Name: !Ref InstanceProfile

  AutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      MinSize: 2
      MaxSize: 10
      DesiredCapacity: 2
      LaunchTemplate:
        LaunchTemplateId: !Ref LaunchTemplate
        Version: !GetAtt LaunchTemplate.LatestVersionNumber
      VPCZoneIdentifier: [!Ref PrivateSubnet1, !Ref PrivateSubnet2]
      TargetGroupARNs: [!Ref TargetGroup]
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300

  # ── Database ──────────────────────────────────────────────────────────────
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: DB subnet group
      SubnetIds: [!Ref PrivateSubnet1, !Ref PrivateSubnet2]

  Database:
    Type: AWS::RDS::DBInstance
    DeletionPolicy: Snapshot
    Properties:
      DBInstanceClass: db.t3.medium
      Engine: postgres
      EngineVersion: "15.4"
      MasterUsername: admin
      MasterUserPassword: !Ref DBPassword
      AllocatedStorage: 100
      StorageEncrypted: true
      MultiAZ: true
      DBSubnetGroupName: !Ref DBSubnetGroup
      VPCSecurityGroups: [!Ref DBSecurityGroup]
      BackupRetentionPeriod: 7
      DeletionProtection: true

Outputs:
  ALBDNS:
    Value: !GetAtt ALB.DNSName
    Export:
      Name: !Sub "${AWS::StackName}-ALB-DNS"
```

### Stack Operations

```bash
# Validate template
aws cloudformation validate-template \
  --template-body file://template.yaml

# Create stack
aws cloudformation create-stack \
  --stack-name prod-app \
  --template-body file://template.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=DBPassword,ParameterValue=$(aws secretsmanager get-secret-value \
      --secret-id prod/db/password --query SecretString --output text) \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --tags Key=Environment,Value=production Key=Team,Value=platform

# Wait for completion
aws cloudformation wait stack-create-complete --stack-name prod-app

# Update stack (change set for safety)
aws cloudformation create-change-set \
  --stack-name prod-app \
  --change-set-name update-instance-type \
  --template-body file://template-v2.yaml \
  --parameters ParameterKey=Environment,UsePreviousValue=true

aws cloudformation describe-change-set \
  --stack-name prod-app \
  --change-set-name update-instance-type

aws cloudformation execute-change-set \
  --stack-name prod-app \
  --change-set-name update-instance-type

# Delete stack
aws cloudformation delete-stack --stack-name prod-app
```

---

## Terraform on AWS

Terraform is cloud-agnostic IaC. Uses HCL (HashiCorp Configuration Language).

### Project Structure

```
terraform/
├── main.tf           # Main resources
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── providers.tf      # Provider config
├── versions.tf       # Version constraints
├── terraform.tfvars  # Variable values (gitignored)
└── modules/
    ├── vpc/
    ├── ec2/
    └── rds/
```

### providers.tf

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Team        = "Platform"
    }
  }
}
```

### variables.tf

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}
```

### main.tf — VPC + EC2

```hcl
# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.environment}-vpc"
  }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.environment}-public-${count.index + 1}"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 11)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.environment}-private-${count.index + 1}"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_eip" "nat" {
  count  = 2
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  depends_on    = [aws_internet_gateway.main]
}

# Security Group
resource "aws_security_group" "web" {
  name_prefix = "${var.environment}-web-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Launch Template + ASG
resource "aws_launch_template" "web" {
  name_prefix   = "${var.environment}-web-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  vpc_security_group_ids = [aws_security_group.web.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.web.name
  }

  metadata_options {
    http_tokens = "required"  # IMDSv2
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd
  EOF
  )

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "web" {
  name_prefix         = "${var.environment}-web-"
  min_size            = 2
  max_size            = 10
  desired_capacity    = 2
  vpc_zone_identifier = aws_subnet.private[*].id
  target_group_arns   = [aws_lb_target_group.web.arn]
  health_check_type   = "ELB"

  launch_template {
    id      = aws_launch_template.web.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.environment}-web"
    propagate_at_launch = true
  }
}
```

### Terraform Commands

```bash
# Initialize (download providers, configure backend)
terraform init

# Format code
terraform fmt -recursive

# Validate
terraform validate

# Plan (preview changes)
terraform plan -var-file=production.tfvars -out=tfplan

# Apply
terraform apply tfplan

# Destroy
terraform destroy -var-file=production.tfvars

# State management
terraform state list
terraform state show aws_vpc.main
terraform state mv aws_instance.old aws_instance.new
terraform import aws_s3_bucket.existing my-existing-bucket

# Workspaces (for multiple environments)
terraform workspace new staging
terraform workspace select production
terraform workspace list
```

---

## CloudFormation vs Terraform

| Feature | CloudFormation | Terraform |
|---------|---------------|-----------|
| Cloud support | AWS only | Multi-cloud |
| State management | AWS managed | S3 + DynamoDB |
| Language | JSON/YAML | HCL |
| Drift detection | ✅ Built-in | ✅ terraform plan |
| Rollback | ✅ Automatic | Manual |
| Modules | Nested stacks | Modules |
| Community | AWS-focused | Large ecosystem |
| Cost | Free | Free (OSS) |

---

## Interview Q&A

### Q1: What is the difference between CloudFormation and Terraform?
**CloudFormation**: AWS-native, no state file to manage (AWS manages it), automatic rollback on failure, tight AWS integration. Best for AWS-only shops.
**Terraform**: Multi-cloud, state file in S3+DynamoDB, manual rollback, larger community and module ecosystem, more flexible. Best for multi-cloud or teams with existing Terraform expertise.

### Q2: What is a CloudFormation change set?
A change set previews what changes CloudFormation will make before executing them. Shows: resources to add, modify, or delete. Critical for production — always use change sets to review before applying. Prevents accidental resource replacement (e.g., RDS instance recreation that causes data loss).

### Q3: How do you manage Terraform state in a team?
Use remote state: S3 bucket for state storage + DynamoDB table for state locking. S3 versioning for state history. Encryption for sensitive data. State locking prevents concurrent applies. Use Terraform workspaces or separate state files per environment. Never commit state files to git.

### Q4: What is CloudFormation drift detection?
Drift = difference between expected state (template) and actual state (AWS resources). Drift occurs when someone manually changes a resource outside CloudFormation. Drift detection compares current resource config to template. Use to identify unauthorized changes. Fix by either updating the template to match reality or reverting the manual change.

### Q5: How do you handle secrets in CloudFormation/Terraform?
**CloudFormation**: Use `{{resolve:secretsmanager:secret-name}}` or `{{resolve:ssm-secure:param-name}}` dynamic references. Never put secrets in template parameters (they appear in CloudFormation console).
**Terraform**: Use `data "aws_secretsmanager_secret_version"` to read secrets at apply time. Mark sensitive variables with `sensitive = true`. Use environment variables for provider credentials. Never hardcode secrets in .tf files or tfvars.
