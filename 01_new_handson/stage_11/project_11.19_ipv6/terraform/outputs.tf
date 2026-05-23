output "vpc_ipv4_cidr"       { value = aws_vpc.main.cidr_block }
output "vpc_ipv6_cidr"       { value = aws_vpc.main.ipv6_cidr_block }
output "public_subnet_ipv6"  { value = aws_subnet.public.ipv6_cidr_block }
output "private_subnet_ipv6" { value = aws_subnet.private.ipv6_cidr_block }
output "eigw_id"             { value = aws_egress_only_internet_gateway.eigw.id }
output "public_ec2_ipv4"     { value = aws_instance.public.public_ip }
output "public_ec2_ipv6"     { value = aws_instance.public.ipv6_addresses }
output "private_ec2_ipv6"    { value = aws_instance.private.ipv6_addresses }
