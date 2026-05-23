output "vpc_id"       { value = aws_vpc.main.id }
output "subnet_ids"   { value = { for k, v in aws_subnet.all : k => v.id } }
output "nat_a_ip"     { value = aws_eip.nat_a.public_ip }
output "nat_b_ip"     { value = aws_eip.nat_b.public_ip }
