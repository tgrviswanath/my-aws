# Reusable Terraform module for EC2 Auto Scaling Group with Launch Template
# Usage:
# module "web_asg" {
#   source            = "./modules/ec2"
#   app_name          = "myapp"
#   environment       = "prod"
#   instance_type     = "t3.medium"
#   ami_id            = data.aws_ami.amazon_linux.id
#   subnet_ids        = module.vpc.private_subnet_ids
#   security_group_ids = [aws_security_group.app.id]
#   target_group_arns = [aws_lb_target_group.app.arn]
#   iam_instance_profile = aws_iam_instance_profile.app.name
#   min_size          = 2
#   max_size          = 20
#   desired_capacity  = 4
#   user_data         = base64encode(file("user_data.sh"))
# }

variable "app_name" {
  description = "Application name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "ami_id" {
  description = "AMI ID for the instances"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for the ASG"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "target_group_arns" {
  description = "ALB target group ARNs"
  type        = list(string)
  default     = []
}

variable "iam_instance_profile" {
  description = "IAM instance profile name"
  type        = string
  default     = null
}

variable "min_size" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "desired_capacity" {
  description = "Desired number of instances"
  type        = number
  default     = 2
}

variable "user_data" {
  description = "Base64-encoded user data script"
  type        = string
  default     = null
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 30
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = false
}

variable "cpu_target" {
  description = "Target CPU utilization for auto scaling (%)"
  type        = number
  default     = 60
}

variable "kms_key_arn" {
  description = "KMS key ARN for EBS encryption"
  type        = string
  default     = null
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}

locals {
  common_tags = merge({
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "Terraform"
  }, var.tags)
}

# ── Launch Template ───────────────────────────────────────────────────────────
resource "aws_launch_template" "main" {
  name_prefix   = "${var.app_name}-${var.environment}-"
  image_id      = var.ami_id
  instance_type = var.instance_type

  vpc_security_group_ids = var.security_group_ids

  dynamic "iam_instance_profile" {
    for_each = var.iam_instance_profile != null ? [1] : []
    content {
      name = var.iam_instance_profile
    }
  }

  # Enforce IMDSv2
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    http_endpoint               = "enabled"
  }

  # Encrypted root volume
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = var.root_volume_size
      volume_type           = "gp3"
      encrypted             = true
      kms_key_id            = var.kms_key_arn
      delete_on_termination = true
    }
  }

  monitoring {
    enabled = var.enable_detailed_monitoring
  }

  user_data = var.user_data

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "${var.app_name}-${var.environment}"
    })
  }

  tag_specifications {
    resource_type = "volume"
    tags = local.common_tags
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

# ── Auto Scaling Group ────────────────────────────────────────────────────────
resource "aws_autoscaling_group" "main" {
  name_prefix         = "${var.app_name}-${var.environment}-"
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.desired_capacity
  vpc_zone_identifier = var.subnet_ids
  target_group_arns   = var.target_group_arns
  health_check_type   = length(var.target_group_arns) > 0 ? "ELB" : "EC2"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.main.id
    version = "$Latest"
  }

  # Instance refresh for zero-downtime updates
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 90
      instance_warmup        = 300
    }
  }

  dynamic "tag" {
    for_each = merge(local.common_tags, { Name = "${var.app_name}-${var.environment}" })
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [desired_capacity]
  }
}

# ── Target Tracking Scaling Policy ───────────────────────────────────────────
resource "aws_autoscaling_policy" "cpu_tracking" {
  name                   = "${var.app_name}-${var.environment}-cpu-tracking"
  autoscaling_group_name = aws_autoscaling_group.main.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value       = var.cpu_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# ── CloudWatch Alarms ─────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.app_name}-${var.environment}-high-cpu"
  alarm_description   = "EC2 ASG CPU utilization above 80%"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.main.name
  }

  tags = local.common_tags
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "asg_name" {
  description = "Auto Scaling Group name"
  value       = aws_autoscaling_group.main.name
}

output "asg_arn" {
  description = "Auto Scaling Group ARN"
  value       = aws_autoscaling_group.main.arn
}

output "launch_template_id" {
  description = "Launch Template ID"
  value       = aws_launch_template.main.id
}

output "launch_template_latest_version" {
  description = "Latest Launch Template version"
  value       = aws_launch_template.main.latest_version
}
