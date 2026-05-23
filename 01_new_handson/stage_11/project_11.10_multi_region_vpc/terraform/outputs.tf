output "vpc_east_id"  { value = aws_vpc.east.id }
output "vpc_west_id"  { value = aws_vpc.west.id }
output "peering_id"   { value = aws_vpc_peering_connection.peer.id }
