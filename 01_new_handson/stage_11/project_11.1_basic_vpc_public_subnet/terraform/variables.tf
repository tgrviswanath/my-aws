variable "region" {
  default = "us-east-1"
}

variable "my_ip" {
  description = "Your IP in CIDR notation for SSH access, e.g. 1.2.3.4/32"
  type        = string
}

variable "key_name" {
  description = "EC2 key pair name"
  type        = string
}
