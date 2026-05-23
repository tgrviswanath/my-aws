variable "region"               { default = "us-east-1" }
variable "strongswan_public_ip" {
  type        = string
  description = "Public IP of the strongSwan EC2 instance (simulated on-premises)"
}
