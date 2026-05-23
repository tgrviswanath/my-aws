# Notes — Project 11.15

## RAM Share Auto-Accept
When RAM sharing is enabled in AWS Organizations, shares to accounts in the same
org are auto-accepted. Without Organizations, the recipient must manually accept.

## PHZ Cross-Account Association Steps
1. Owner account: `create-vpc-association-authorization` (grants permission)
2. Participant account: `associate-vpc-with-hosted-zone` (performs association)
3. Owner account: `delete-vpc-association-authorization` (cleanup, optional)

## Security Consideration
Shared subnets inherit the VPC's route tables and NACLs from the owner account.
Participant accounts cannot change these — good for centralized security control.
But participant accounts can create their own SGs within the shared VPC.

## Tagging Strategy for Multi-Account
Tag every resource with:
- `Account`: management | dev | prod
- `Owner`: team name
- `CostCenter`: billing code
This is critical for cost allocation across accounts.
