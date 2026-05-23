variable "region"         { default = "us-east-1" }
variable "mgmt_profile"   { type = string; description = "AWS CLI profile for management account" }
variable "dev_profile"    { type = string; description = "AWS CLI profile for dev account" }
variable "dev_account_id" { type = string; description = "AWS account ID of the dev account" }
