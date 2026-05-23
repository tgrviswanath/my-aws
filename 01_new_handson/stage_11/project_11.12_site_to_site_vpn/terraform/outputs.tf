output "vpn_id"              { value = aws_vpn_connection.vpn.id }
output "tunnel1_outside_ip"  { value = aws_vpn_connection.vpn.tunnel1_address }
output "tunnel2_outside_ip"  { value = aws_vpn_connection.vpn.tunnel2_address }
output "tunnel1_psk"         { value = aws_vpn_connection.vpn.tunnel1_preshared_key; sensitive = true }
output "tunnel2_psk"         { value = aws_vpn_connection.vpn.tunnel2_preshared_key; sensitive = true }
