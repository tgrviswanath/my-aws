variable "region"              { default = "us-east-1" }
variable "bgp_router_public_ip" {
  type        = string
  description = "Public IP of the EC2 running Bird BGP daemon"
}
