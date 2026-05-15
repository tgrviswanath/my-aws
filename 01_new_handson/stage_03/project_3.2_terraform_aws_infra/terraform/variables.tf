variable "region"   { default = "ap-south-1" }
variable "project"  { default = "handson" }
variable "environment" {
  default = "dev"
  validation {
    condition     = contains(["dev", "qa", "prod"], var.environment)
    error_message = "Must be dev, qa, or prod."
  }
}

variable "vpc_cidr"  { default = "10.0.0.0/16" }
variable "azs"       { default = ["ap-south-1a", "ap-south-1b"] }

variable "key_name"  { description = "EC2 key pair name" }

variable "desired_capacity" { default = 2 }
variable "min_size"         { default = 1 }
variable "max_size"         { default = 4 }

variable "db_name"     { default = "appdb" }
variable "db_username" { default = "admin" }
variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "my_ip" {
  description = "Your IP for SSH access (e.g. 1.2.3.4/32)"
  type        = string
}
