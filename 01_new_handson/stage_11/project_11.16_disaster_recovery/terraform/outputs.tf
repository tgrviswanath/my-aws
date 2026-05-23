output "primary_alb_dns"  { value = aws_lb.primary.dns_name }
output "dr_alb_dns"       { value = aws_lb.dr.dns_name }
output "health_check_id"  { value = aws_route53_health_check.primary.id }
