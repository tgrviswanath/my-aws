output "s3_endpoint_id"       { value = aws_vpc_endpoint.s3.id }
output "dynamodb_endpoint_id" { value = aws_vpc_endpoint.dynamodb.id }
output "ssm_endpoint_id"      { value = aws_vpc_endpoint.ssm.id }
