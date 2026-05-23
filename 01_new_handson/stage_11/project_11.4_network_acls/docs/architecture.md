# Architecture Notes — Project 11.4

## Why Ephemeral Ports Matter
TCP connections use a random high port (1024-65535) for the return traffic.
Since NACLs are stateless, you MUST explicitly allow these ports outbound (for responses
to inbound requests) and inbound (for responses to outbound requests).

## NACL vs SG Summary
| | NACL | Security Group |
|--|--|--|
| Stateful | No | Yes |
| Level | Subnet | Instance |
| Rule types | Allow + Deny | Allow only |
| Evaluation | Ordered (lowest first) | All rules evaluated |
| Return traffic | Must explicitly allow | Automatic |

## Defense in Depth
Use NACLs as a coarse filter (block entire IP ranges, block known bad ports)
and SGs as fine-grained per-instance control. Both layers together = defense in depth.
