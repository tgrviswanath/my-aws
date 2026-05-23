output "cluster_name"  { value = aws_ecs_cluster.main.name }
output "alb_dns_name"  { value = aws_lb.alb.dns_name }
output "namespace_id"  { value = aws_service_discovery_private_dns_namespace.local.id }
