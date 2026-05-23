variable "region"            { default = "us-east-1" }
variable "vpc_id"            { type = string; description = "VPC ID" }
variable "public_subnet_ids" { type = list(string); description = "List of 2 public subnet IDs" }
