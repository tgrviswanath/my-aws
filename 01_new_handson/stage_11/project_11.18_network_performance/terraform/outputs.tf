output "ec2_a_public_ip"  { value = aws_instance.a.public_ip }
output "ec2_b_public_ip"  { value = aws_instance.b.public_ip }
output "ec2_a_private_ip" { value = aws_instance.a.private_ip }
output "ec2_b_private_ip" { value = aws_instance.b.private_ip }
output "placement_group"  { value = aws_placement_group.cluster.name }
