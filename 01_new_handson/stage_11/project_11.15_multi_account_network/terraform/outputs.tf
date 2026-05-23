output "shared_vpc_id"    { value = aws_vpc.shared.id }
output "shared_subnet_a"  { value = aws_subnet.shared_a.id }
output "shared_subnet_b"  { value = aws_subnet.shared_b.id }
output "ram_share_arn"    { value = aws_ram_resource_share.share.arn }
output "phz_id"           { value = aws_route53_zone.internal.zone_id }
