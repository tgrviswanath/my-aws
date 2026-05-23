variable "region"      { default = "us-east-1" }
variable "environment" { default = "dev"; description = "dev | staging | prod" }
variable "vpc_cidr"    { default = "10.0.0.0/16" }
variable "enable_nat"  { default = true; description = "Set false to skip NAT Gateway (saves cost)" }
