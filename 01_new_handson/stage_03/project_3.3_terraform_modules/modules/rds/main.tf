# modules/rds/main.tf

variable "name_prefix"  { type = string }
variable "vpc_id"       { type = string }
variable "subnet_ids"   { type = list(string) }
variable "app_sg_id"    { type = string }
variable "db_name"      { default = "appdb" }
variable "db_username"  { default = "admin" }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "instance_class" { default = "db.t3.micro" }
variable "multi_az"       { default = false }
variable "common_tags" {
  type    = map(string)
  default = {}
}

resource "aws_security_group" "rds" {
  name   = "${var.name_prefix}-rds-sg"
  vpc_id = var.vpc_id
  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [var.app_sg_id]
    description     = "MySQL from app tier"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-rds-sg" })
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.name_prefix}-db-subnet-group"
  subnet_ids = var.subnet_ids
  tags       = merge(var.common_tags, { Name = "${var.name_prefix}-db-subnet-group" })
}

resource "aws_db_instance" "mysql" {
  identifier              = "${var.name_prefix}-mysql"
  engine                  = "mysql"
  engine_version          = "8.0"
  instance_class          = var.instance_class
  allocated_storage       = 20
  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  publicly_accessible     = false
  multi_az                = var.multi_az
  backup_retention_period = 0
  skip_final_snapshot     = true
  tags                    = merge(var.common_tags, { Name = "${var.name_prefix}-mysql" })
}

output "endpoint"  { value = aws_db_instance.mysql.endpoint }
output "rds_sg_id" { value = aws_security_group.rds.id }
