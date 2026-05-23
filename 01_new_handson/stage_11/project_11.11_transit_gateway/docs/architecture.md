# Architecture Notes — Project 11.11

## TGW vs VPC Peering
```
VPC Peering (non-transitive):          Transit Gateway (transitive):
A ←→ B                                  A ←→ TGW ←→ B
B ←→ C                                  B ←→ TGW ←→ C
A cannot reach C                        A can reach C via TGW
Need N*(N-1)/2 peerings for N VPCs     Need N attachments only
```

## TGW Route Table Segmentation
```
Default RT (shared):  VPC-A, VPC-B, VPC-C all connected
Isolated RT:          VPC-C isolated — cannot reach A or B
                      Use case: prod/dev separation
```

## TGW Attachment Types
- VPC attachment (this project)
- VPN attachment (Project 11.12)
- Direct Connect Gateway attachment
- Peering attachment (cross-region TGW peering)
