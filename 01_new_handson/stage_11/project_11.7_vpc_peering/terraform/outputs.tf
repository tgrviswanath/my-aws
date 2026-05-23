output "vpc_a_id"    { value = aws_vpc.a.id }
output "vpc_b_id"    { value = aws_vpc.b.id }
output "peering_id"  { value = aws_vpc_peering_connection.peer.id }
