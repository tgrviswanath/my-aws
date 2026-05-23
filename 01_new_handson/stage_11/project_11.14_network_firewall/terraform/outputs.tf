output "firewall_id"     { value = aws_networkfirewall_firewall.nfw.id }
output "firewall_arn"    { value = aws_networkfirewall_firewall.nfw.arn }
output "policy_arn"      { value = aws_networkfirewall_firewall_policy.policy.arn }
