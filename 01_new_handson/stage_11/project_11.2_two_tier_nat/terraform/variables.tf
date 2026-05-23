variable "region"   { default = "us-east-1" }
variable "my_ip"    { type = string; description = "Your IP CIDR e.g. 1.2.3.4/32" }
variable "key_name" { type = string; description = "EC2 key pair name" }
