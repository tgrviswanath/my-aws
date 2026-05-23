output "vpc_id"            { value = aws_vpc.main.id }
output "vpc_cidr"          { value = aws_vpc.main.cidr_block }
output "public_subnet_ids" { value = aws_subnet.public[*].id }
output "app_subnet_ids"    { value = aws_subnet.private_app[*].id }
output "db_subnet_ids"     { value = aws_subnet.private_db[*].id }
output "nat_gateway_id"    { value = var.enable_nat ? aws_nat_gateway.nat[0].id : "disabled" }
