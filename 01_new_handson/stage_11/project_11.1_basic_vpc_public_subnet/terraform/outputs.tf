output "vpc_id"         { value = aws_vpc.main.id }
output "subnet_id"      { value = aws_subnet.public.id }
output "igw_id"         { value = aws_internet_gateway.igw.id }
output "ec2_public_ip"  { value = aws_instance.web.public_ip }
output "ec2_public_dns" { value = aws_instance.web.public_dns }
