terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-11-14" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags = { Name = "public-11-14" }
}

resource "aws_subnet" "firewall" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.region}a"
  tags = { Name = "firewall-11-14" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = "${var.region}a"
  tags = { Name = "private-11-14" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "igw-11-14" }
}

# Stateless rule group — forward HTTP/HTTPS to stateful engine
resource "aws_networkfirewall_rule_group" "stateless" {
  name     = "stateless-rg-11-14"
  type     = "STATELESS"
  capacity = 100

  rule_group {
    rules_source {
      stateless_rules_and_custom_actions {
        stateless_rule {
          priority = 10
          rule_definition {
            actions = ["aws:forward_to_sfe"]
            match_attributes {
              protocols = [6]
              source { address_definition = "10.0.3.0/24" }
              destination_port { from_port = 443; to_port = 443 }
            }
          }
        }
        stateless_rule {
          priority = 20
          rule_definition {
            actions = ["aws:forward_to_sfe"]
            match_attributes {
              protocols = [6]
              source { address_definition = "10.0.3.0/24" }
              destination_port { from_port = 80; to_port = 80 }
            }
          }
        }
      }
    }
  }
  tags = { Name = "stateless-rg-11-14" }
}

# Stateful rule group — domain block list
resource "aws_networkfirewall_rule_group" "stateful_domains" {
  name     = "stateful-domain-11-14"
  type     = "STATEFUL"
  capacity = 100

  rule_group {
    rules_source {
      rules_source_list {
        generated_rules_type = "DENYLIST"
        target_types         = ["HTTP_HOST", "TLS_SNI"]
        targets              = [".malware-test.com", ".blocked-site.com"]
      }
    }
  }
  tags = { Name = "stateful-domain-11-14" }
}

# Firewall Policy
resource "aws_networkfirewall_firewall_policy" "policy" {
  name = "policy-11-14"

  firewall_policy {
    stateless_default_actions          = ["aws:drop"]
    stateless_fragment_default_actions = ["aws:drop"]

    stateless_rule_group_reference {
      priority     = 1
      resource_arn = aws_networkfirewall_rule_group.stateless.arn
    }

    stateful_rule_group_reference {
      resource_arn = aws_networkfirewall_rule_group.stateful_domains.arn
    }
  }
  tags = { Name = "policy-11-14" }
}

# Network Firewall
resource "aws_networkfirewall_firewall" "nfw" {
  name                = "nfw-11-14"
  firewall_policy_arn = aws_networkfirewall_firewall_policy.policy.arn
  vpc_id              = aws_vpc.main.id

  subnet_mapping {
    subnet_id = aws_subnet.firewall.id
  }
  tags = { Name = "nfw-11-14" }
}
