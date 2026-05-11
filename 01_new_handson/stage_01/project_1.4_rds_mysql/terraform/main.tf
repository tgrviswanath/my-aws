terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region"      { default = "us-east-1" }
variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}
variable "ec2_sg_id" {
  description = "Security group ID of the EC2 instance that will connect to RDS"
  type        = string
}

data "aws_vpc" "default" { default = true }

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ─── Security Group for RDS ───────────────────────────────────────────────────

resource "aws_security_group" "rds" {
  name        = "rds-sg"
  description = "Allow MySQL from EC2 only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "MySQL from EC2"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [var.ec2_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Project = "handson", Stage = "stage-01" }
}

# ─── DB Subnet Group ──────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "rds-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = { Project = "handson", Stage = "stage-01" }
}

# ─── RDS MySQL Instance ───────────────────────────────────────────────────────

resource "aws_db_instance" "mysql" {
  identifier        = "mysql-lab-01"
  engine            = "mysql"
  engine_version    = "8.0"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "appdb"
  username = "admin"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  skip_final_snapshot = true  # set to false in production

  tags = {
    Name        = "mysql-lab-01"
    Project     = "handson"
    Stage       = "stage-01"
    Environment = "learning"
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "rds_endpoint" { value = aws_db_instance.mysql.endpoint }
output "rds_port"     { value = aws_db_instance.mysql.port }
output "db_name"      { value = aws_db_instance.mysql.db_name }
